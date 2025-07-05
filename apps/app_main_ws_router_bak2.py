
from pathlib import Path
import sys 
import os 
import json
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)


from models.langchain_models import llm_qwen_14B
from utils.util import *
from sql_processing.text2sql import schema_linking, sql_gen
from langchain_community.utilities import SQLDatabase
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter, FastAPI
import os
from module.prompt import *
from models.langchain_models import llm_qwen_14B
from utils.util import *
from sql_processing.text2sql import schema_linking, sql_gen
from configs import config as config
from langchain_community.utilities import SQLDatabase
from module.main_llm import *
from online_sql import sql_path
from models.create_chain import *
import simplejson
import uvicorn
from fastapi import FastAPI, WebSocket
from webui_models.utils import query_insight_generator, obtain_detail_data
from apps.websocket_manager import clients
from apps.websocket_manager import send_to_clients
from pymilvus import MilvusClient
from operator_workflow.milvus_client import MilvusOperation
from operator_workflow.workflow import app_retrieve, app_retrieve_extraction, app_retrieve_summary
import datetime
from sql_processing.view_manager import drop_view

app = FastAPI()

app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
) # 中间件白名单


config_dict = {}  # 主程序里加入到缓存里的变量构成的字典


class ObtainDataItem(BaseModel):
    query: str = '近1年哪些小区有设备维修的需求'
    task_type:  Literal['SQL', '内容抽取', '内容总结', 'All'] = Field(default='All')
 

# WebSocket路由 
@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            validated_data = ObtainDataItem(**data)
            query = validated_data.query
            task_type = validated_data.task_type

            view_values = '' # 暂且不设置视图
            filtered_list = []

            logger.info(f'查询的问题为：  {query}')
            # 读取配置加载接口得到的配置信息
            table_schema_dict = config_dict['table_schema_dict'] 

            full_related_dict = config_dict['full_related_dict']  #{table1: {column1: distinct_values, ...}, table2: {}, ...}
            full_abbr_dict = config_dict['full_abbr_dict']  #{table1: {column1: distinct_values, ...}, ...}
            

            unstructured_table = config_dict['target_table']
            unstructured_column = config_dict['unstructured_column'] 
            milvus_field_type = config_dict['milvus_field_type'] 
            milvus_opt = config_dict['milvus_opt']
            mysql_db = config_dict['mysql_db']
            

            full_tables = list(table_schema_dict.keys())
            full_schema = '\n\n'.join(list(table_schema_dict.values()))

            start_time = time.time() 

            # 获取查询的表（可以是多表）
            if len(full_tables) == 1:
                use_tables = full_tables
                explanations = "仅有1张表可选"
            elif len(full_tables) > 1:
                select_tables = await table_chain.ainvoke({"table_list": full_tables , 
                                                        "schema": full_schema, 
                                                        "question": query
                                                        })
                use_tables = select_tables['tables']
                use_tables = use_tables if set(use_tables).issubset(set(full_tables)) else full_tables
                explanations = select_tables['explanations']
            else:
                use_tables = []
                logger.error('可选择的表不允许为空')
            schema = '\n\n'.join([table_schema_dict[table] for table in use_tables])
            
            logger.info(f'use_tables: {use_tables}, explanations: {explanations}')

            old_linking_columns, new_linking_columns = await schema_linking(query, schema, full_related_dict, 
                                         examples='\n'.join(filtered_list), chain=schema_linking_chain)
            logger.info(f"schema linking: {new_linking_columns}")
            logger.info(f"old schema linking: {old_linking_columns}")
            

            target_columns = new_linking_columns['target_columns']
            condition_columns = new_linking_columns['condition_columns']
            
            print(time.time() - start_time)
            # 调用流式生成器并实时传输数据
            async for chunk in query_insight_generator(explanation_chain, query, schema, new_linking_columns):
                await websocket.send_text(chunk)  # 将每个 chunk 发送给客户端
            await websocket.send_text('DONE')

            # 如果不指定，则进行模型决策
            if task_type == 'All':
                # 判断查询列是否在结构化字段里
                if  unstructured_table in use_tables and unstructured_column in target_columns: 
                    # 意味着可能需要语义分析
                    res = await task_aware_chain.ainvoke({'query': query, })
                    task_type = res['TaskType']
                else:
                    task_type = 'SQL'

            logger.info(f'任务类型: {task_type}')

            if task_type in ['SQL', '内容分类']: 
                # 生成候选sql查询语句,并发生给前端
                obtain_data, sql_result, params, view_table_names = await sql_path(query, use_tables, mysql_db, new_linking_columns, schema, view_values, 
                                                                 sql_gen_chain,  sql_feedback_chain, full_abbr_dict,
                                                                unstructured_table, unstructured_column, ner_clf_chain, app_retrieve, milvus_opt)
                
                await send_to_clients(simplejson.dumps({"sql_gen": 'SELECT x'}, ensure_ascii=False))
                print('@@@@@@@@@@@@@@@', simplejson.dumps({"sql_gen": sql_result['sql_std']}, ensure_ascii=False))
                await send_to_clients(simplejson.dumps({"sql_gen": sql_result['sql_std']}, ensure_ascii=False))
                
            elif task_type in ['内容抽取', '内容总结']:  
                if len(use_tables) > 1 or (unstructured_table not in use_tables):
                    await send_to_clients(simplejson.dumps( {"information": "提示：此功能无法支持该问题的查询"}, ensure_ascii=False))
                    continue
                
                # 只会使用1个表，且该表就是unstructured_table
                # 生成filter_exp (会过滤掉非 结构化字段)
                filter_expr, unstructrued_value = generation_filter_expr(milvus_field_type, condition_columns, unstructured_column, 
                                                                        ner_clf_chain, text2datetime_chain, )  
                logger.info(f'过滤表达式： {filter_expr}; 查询问题： {unstructrued_value}')
                # 执行
                if task_type == '内容总结':
                    final_state = await app_retrieve_summary.ainvoke(
                        {"unstr_value": unstructrued_value, "filter_exp":  filter_expr, "milvus_opt": milvus_opt})
                    
                elif task_type == '内容抽取':
                    final_state = await app_retrieve_extraction.ainvoke(
                        { 'query': query, "unstr_value": unstructrued_value, "filter_exp":  filter_expr,"milvus_opt": milvus_opt})
                        # [{"企业": "孔乙己酒家", "数量": 2}, {}, {}]
                obtain_data = final_state['outputs'] 
            else:
                print('{} 任务类型目前还不支持处理'.format(task_type))
                
            # 将查询问题所对应的结果发送给前端
            def custom_serializer(obj):
                if isinstance(obj, (datetime.datetime,datetime.date) ):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
            await send_to_clients(simplejson.dumps({"response": obtain_data}, default=custom_serializer, ensure_ascii=False))
            
            # 获取数据明细
            # 将与结果相关的数据明细发送给前端
            if task_type in ['SQL', '内容分类']:
                pattern = r"(?i)(SELECT\s+)(.*?)(\s+FROM)"
                modified_sql = re.sub(pattern, lambda match: f"{match.group(1)}*{match.group(3)}", sql_result['sql_view'], flags=re.IGNORECASE)
                modified_sql_group_remove = remove_group_by(modified_sql)
                print('-=-=-=', modified_sql_group_remove, params, )
                execute_result = sql_execute(mysql_db, modified_sql_group_remove, schema, params, sql_feedback_chain)
                
                result_detail = eval(execute_result) if  execute_result != '' else [{}]
            else: 
                result_detail = [{}] 
            await send_to_clients(simplejson.dumps({ "data_detail": result_detail[:1000], "sql":modified_sql_group_remove, "param":params}, 
                                                default=str,ensure_ascii=False))  # 会把datatime转成字符串，另外一种是把result_detail转换字符串: str(result_detail)
            
            # 将对结果的解读发送给前端
            TopK_data = obtain_data[:15]
            result_insight = chat_chain.invoke({ "query": query, "obtain_data": TopK_data})
            await send_to_clients(simplejson.dumps( {"result_insight": result_insight}, ensure_ascii=False))
            
            # 将接下来的推荐问题发生给前端
            query_recommands = recommand_chain.invoke({ "query": query, "schema": schema, "obtain_data": TopK_data})
            await send_to_clients(json.dumps({"result_recommand": query_recommands}, ensure_ascii=False))
            
            await send_to_clients(json.dumps({'connect_flag': 'END'}, ensure_ascii=False))
            # 执行完sql之后删除视图
            drop_view(mysql_db, view_table_names)

            logger.info(f'query: {query} 处理完毕')
    except Exception as e:
        await send_to_clients(json.dumps({'connect_flag': 'ERROR'}, ensure_ascii=False))
        # 执行完sql之后删除视图
        # drop_view(mysql_db, view_table_names)
        # 出现错误时，移除客户端连接
        logger.error(f'Unexpected error occured:{e}', exc_info=True)
        clients.remove(websocket)




@app.post('/load_config', summary='加载数据源配置信息')
async def load_config(databaseId: int):


    # 获取配置信息
    mysql_db, param_db, client, _, unstructured_column, target_table, selected_tables, params_dict \
          = obtain_database_config(config.param_uri, config.milvus_uri, db_id=databaseId, )
    collection_name = target_table
    # 选中的表
    selected_table_names = selected_tables.split(',')
    if len(selected_table_names) == 0: # 如果忘记选择表了导致为空，则以全部的表作为选择的表
        selected_table_names = mysql_db.get_table_names()

    print(params_dict)


    # 获取某个表的元数据获取
    table_schema_dict = {}
    columns_map = {}
    full_abbr_dict = {}
    full_related_dict = {}

    for selected_table_name in selected_table_names:

        table_schema, table_abbr_columns, table_related_columns, table_columns_map = \
                params_parser(param_db, 'field_metadata', selected_table_name)
        table_schema_dict[selected_table_name] = table_schema

        if selected_table_name == target_table:
            columns_map = table_columns_map
        # 关联列
        table_related_dict = get_distinct_values(mysql_db, selected_table_name, table_related_columns)
        if table_related_dict: # 任何一个表如果有关联列，则保存起来
            full_related_dict.update({selected_table_name: table_related_dict})
        # 缩写列
        table_abbr_dict = get_distinct_values(mysql_db, selected_table_name, table_abbr_columns)
        if table_abbr_dict:
            full_abbr_dict.update({selected_table_name: table_abbr_dict})

    # logger.info(f'获取的列映射: {columns_map}')
    # logger.info(f'获取的每个选中表的元数据: {table_schema_dict}')

    # logger.info(f'获取每个表中的关联列: {full_related_dict}')
    # logger.info(f'获取每个表中的缩写列: {full_abbr_dict}')
    

    # 获取时间类型但是是字符串表示的字段
    datetime_str_cols = []
    if client:  # if client 等价于 if is_semantic_analysis
        first_lines = mysql_db.run(f'SELECT * FROM {target_table} LIMIT 1', include_columns=True)
        first_lines = eval(first_lines)
        for k, v in first_lines[0].items():
            if isinstance(v, str) and is_valid_datetime(v):
                datetime_str_cols.append(k)

        # 只有开启语义时才会重写这部分的配置
        
        config.large_step = int(params_dict['large_step'])
        config.small_step = int(params_dict['small_step'])
        config.window_size = int(params_dict['window_size'])
        config.min_samples = int(params_dict['min_samples'])
        config.limit = int(params_dict['max_samples'])

    # 重写配置
    config.datetime_type_field = datetime_str_cols
    config.columns_map = columns_map
    config.unstructured_column = unstructured_column
    config.is_semantic_analysis = 1 if client else 0
    config.is_abbr_analysis = 1 if full_abbr_dict else 0 
    

    # 开启语义分析时，client 不为None
    if client:
        collection_info = client.describe_collection(collection_name= collection_name)
        # 'fields': [{'field_id': 100, 'name': 'id', 'description': '', 'type': <DataType.INT64: 5>, 'params': {}, 'is_primary': True}, ]
        milvus_field_type = {each_field['name']: each_field['type'].name for each_field in collection_info['fields']} # <DataType.INT64: 5> ==> .name, .value 获取枚举类型的数据
        # {'id': 'INT64'}
        bm25_ef_path = os.path.join(config.data_save_dir, f'{collection_name}.json')
        
        milvus_opt = MilvusOperation(uri=config.milvus_uri, collection_name= collection_name, bm25_ef_path=bm25_ef_path)
        
    else:
        milvus_field_type = {}
        milvus_opt = None 

    config_dict['table_schema_dict'] = table_schema_dict  # 包含了选择的表名 
    config_dict['full_related_dict'] = full_related_dict
    config_dict['full_abbr_dict'] = full_abbr_dict 
    config_dict['target_table'] = target_table
    config_dict['unstructured_column'] = unstructured_column
  
    config_dict['milvus_field_type']  = milvus_field_type
    config_dict['milvus_opt'] = milvus_opt 
    config_dict['mysql_db'] = mysql_db
    

    
    return {'result': 'Done'}
    


if __name__ == '__main__':

    # 创建数据保存文件夹
    if not os.path.exists(config.data_save_dir):
        os.makedirs(config.data_save_dir)
    log_dir = os.path.join(config.data_save_dir, config.log_dir_name)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    
    uvicorn.run(app=app, host='0.0.0.0', port=33063)






    """
    logger.info('案例库查询')
    top_indices = retrieve_cases(query=query, embedding_corpus=embedding_corpus)
    select_case_list = [corpus[i]  for i in top_indices]
    filtered_list = [str(item) for item in examples if item['query'] in select_case_list]
    logger.info(f'案例库查询结果: {filtered_list}')
    """

    """
    # 案例库：
    with open(f'examples_{config.data_table_names[0]}.json', 'r', encoding='utf-8') as f_json:
        examples = json.load(f_json)
    
    # 案例库的语料
    corpus = [each_data['query'] for each_data in examples]
    embedding_corpus = embedding_bge(corpus)
    """

