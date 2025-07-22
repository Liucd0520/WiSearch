
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
from operator_workflow.workflow import app_retrieve, app_retrieve_extraction, app_retrieve_summary, app_simorder
import datetime
from sql_processing.view_manager import drop_view
from typing import List 
from collections import defaultdict

app = FastAPI()

app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
) # 中间件白名单


config_dict = defaultdict(dict)  # 主程序里加入到缓存里的变量构成的字典


class ObtainDataItem(BaseModel):
    query: str = '近1年哪些小区有设备维修的需求'
    task_type:  Literal['SQL', '内容抽取', '内容总结', '多人同诉', 'All'] = Field(default='All')
    databaseIds: List[int]
 

# WebSocket路由 
@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    
    await websocket.accept()
    clients.append(websocket)
    if len(clients) > 1:    # 第二次再查询clients会新增一个websocket连接，但是之前的那个由于前端断掉所以已经不可用
        # clients = clients[-1:]
        clients.reverse()
        clients.pop()
    # 正式进入查询模块
    try:
        message = await websocket.receive_text()
        data = json.loads(message)
        validated_data = ObtainDataItem(**data)
        query = validated_data.query
        task_type = validated_data.task_type
        databaseIds = validated_data.databaseIds

        view_values = '' # 暂且不设置视图
        filtered_list = []

        logger.info(f'查询的问题为：  {query}')
        # 选择某个库
        if len(databaseIds) == 1:
            databaseId = databaseIds[0]
            database_explanations = '仅有1个数据库被选中'
            
        else:
            # mapping = {db_id: config_dict['description'][db_id] for db_id in databaseIds}
            mapping = {db_id: list(config_dict['table_schema_dict'][db_id].values()) for db_id in databaseIds}
            logger.info(f'所有库的schema长度为： {len(str(mapping))}')
            selected_db = await database_chain.ainvoke({"database_id": list(mapping.keys()), 
                                          "database_description": mapping, 
                                          "question": query})
            
            databaseId = selected_db['databaseId']
            database_explanations = selected_db['explanations']
            databaseId = int(databaseId) if int(databaseId) in list(mapping.keys()) else -1
        logger.info(f'use_databaseId: {databaseId}, database_explanations: {database_explanations}')
        

        if databaseId == -1:
            logger.error('该查询问题没有找到合适的数据库，请换一种说法 ...')
            raise ValueError("该查询问题没有找到合适的数据库，请换一种说法 ...")
            

        # 读取配置加载接口得到的配置信息
        table_schema_dict = config_dict['table_schema_dict'][databaseId]
        full_related_dict = config_dict['full_related_dict'][databaseId]  #{table1: {column1: distinct_values, ...}, table2: {}, ...}
        full_abbr_dict = config_dict['full_abbr_dict'][databaseId]  #{table1: {column1: distinct_values, ...}, ...}
        

        unstructured_table = config_dict['target_table'][databaseId]
        unstructured_column = config_dict['unstructured_column'][databaseId]
        milvus_field_type = config_dict['milvus_field_type'][databaseId]
        milvus_opt = config_dict['milvus_opt'][databaseId]
        mysql_db = config_dict['mysql_db'][databaseId]
        config.columns_map = config_dict['config_param_dict'][databaseId]['columns_map']
        config.unstructured_column = config_dict['config_param_dict'][databaseId]['unstructured_column']
        config.is_semantic_analysis = config_dict['config_param_dict'][databaseId]['is_semantic_analysis']
        config.datetime_type_field = config_dict['config_param_dict'][databaseId]['datetime_type_field']
        config.is_abbr_analysis = config_dict['config_param_dict'][databaseId]['is_abbr_analysis']

        if milvus_opt:
            config.large_step = config_dict['config_param_dict'][databaseId]['large_step']
            config.small_step = config_dict['config_param_dict'][databaseId]['small_step']
            config.window_size = config_dict['config_param_dict'][databaseId]['window_size']
            config.min_samples = config_dict['config_param_dict'][databaseId]['min_samples']
            config.limit = config_dict['config_param_dict'][databaseId]['limit']


        full_tables = list(table_schema_dict.keys())
        full_schema = '\n\n'.join(list(table_schema_dict.values()))

        start_time = time.time() 

        # 获取查询的表（可以是多表）
        if len(full_tables) == 1:
            use_tables = full_tables
            table_explanations = "仅有1张表可选"
        elif len(full_tables) > 1:
            select_tables = await table_chain.ainvoke({"table_list": full_tables , 
                                                    "schema": full_schema, 
                                                    "question": query
                                                    })
            use_tables = select_tables['tables']
            use_tables = use_tables if set(use_tables).issubset(set(full_tables)) else full_tables
            table_explanations = select_tables['explanations']
        else:
            use_tables = []
            logger.error('可选择的表不允许为空')
        schema = '\n\n'.join([table_schema_dict[table] for table in use_tables])
        
        logger.info(f'use_tables: {use_tables}, table_explanations: {table_explanations}')

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
            if '多人同诉' in query or '多人一诉' in query:
                task_type = '多人同诉'
            else:
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
            
            
            await send_to_clients(simplejson.dumps({"sql_gen": sql_result['sql_std']}, ensure_ascii=False))
            
        elif task_type in ['内容抽取', '内容总结', '多人同诉']:  
            if len(use_tables) > 1 or (unstructured_table not in use_tables):
                await send_to_clients(simplejson.dumps( {"information": "提示：此功能无法支持该问题的查询"}, ensure_ascii=False))
                return 
            
            # 只会使用1个表，且该表就是unstructured_table
            # 生成filter_exp (会过滤掉非 结构化字段)
            filter_expr, unstructrued_value = generation_filter_expr(milvus_field_type, condition_columns, unstructured_column, 
                                                                    ner_clf_chain, text2datetime_chain, )  
            logger.info(f'过滤表达式： {filter_expr}; 查询问题： {unstructrued_value}')
            # 执行
            if task_type == '内容总结':
                final_state = await app_retrieve_summary.ainvoke(
                    {"unstr_value": unstructrued_value, "filter_exp":  filter_expr, "milvus_opt": milvus_opt})
            
            if task_type == '多人同诉':
                final_state = await app_simorder.ainvoke(
                    {"unstr_value": unstructrued_value, "filter_exp":  filter_expr, "milvus_opt": milvus_opt, "schema": schema})
                
            elif task_type == '内容抽取':
                final_state = await app_retrieve_extraction.ainvoke(
                    { 'query': query, "unstr_value": unstructrued_value, "filter_exp":  filter_expr,"milvus_opt": milvus_opt})
                
            
                    # [{"企业": "孔乙己酒家", "数量": 2}, {}, {}]
            
            result_data = final_state['outputs']['result'] # [{"theme1": [doc1, doc2, doc3]}, {"theme2": [doc4, doc5]}]
            detail_data = final_state['outputs']['detail']

            obtain_data = [{'摘要': list(each_result.keys()), "数量": len(list(each_result.values())[0]), "内容": '  |||  '.join(list(each_result.values())[0]) } for each_result in result_data]
            print('obtain_data', obtain_data[0])
        
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
            modified_sql = re.sub(pattern, lambda match: f"{match.group(1)}*{match.group(3)}", sql_result['sql_view'],count=1, flags=re.IGNORECASE)
            detail_sql = remove_group_by(modified_sql)
            logger.info(f'数据明细对应的SQL： {detail_sql}, {params}', )
            execute_result = sql_execute(mysql_db, detail_sql, schema, params, sql_feedback_chain)
            
            result_detail = eval(execute_result) if  execute_result != '' else [{}]
        else: 
            flipped_mapping_dict = {v:k for k, v in config.columns_map.items()}
            detail_expr = f"""{config.columns_map[config.unstructured_column]} IN {detail_data}"""
            mark = milvus_opt.query_with_filter(
            output_fields=list(flipped_mapping_dict.keys()),  
            filter_exp= ' AND '.join([filter_expr, detail_expr]), 
            limit = config.limit)

            # 将MIlvus里的英文字段，换成中文的
            result_detail = [{flipped_mapping_dict[field_en]: data[field_en] for field_en in flipped_mapping_dict.keys()} for data in mark ] 
            detail_sql = filter_expr
            params = {}
            databaseId = -1 

        await send_to_clients(simplejson.dumps({ "data_detail": result_detail[:1000], "sql":detail_sql, "param":params,  "databaseId": databaseId}, 
                                            default=str,ensure_ascii=False))  # 会把datatime转成字符串，另外一种是把result_detail转换字符串: str(result_detail)
        
        print('--xxxxx')
        # 将对结果的解读发送给前端
        if task_type == '多人同诉':
            TopK_data = [{'event': list(each_data.keys())[0], 'count': len(list(each_data.values())[0])} for each_data in obtain_data[:50]]
        else:
            TopK_data = obtain_data[:10]

        result_insight = await chat_chain.ainvoke({ "query": query, "obtain_data": TopK_data})
        await send_to_clients(simplejson.dumps( {"result_insight": result_insight}, ensure_ascii=False))
        
        # 将接下来的推荐问题发生给前端
        query_recommands = await recommand_chain.ainvoke({ "query": query, "schema": schema, "obtain_data": TopK_data})
        await send_to_clients(json.dumps({"result_recommand": query_recommands}, ensure_ascii=False))
        
        await send_to_clients(json.dumps({'connect_flag': 'END'}, ensure_ascii=False))

        # 执行完sql之后删除视图 (目前只针对MySQL数据库)
        if task_type in ['SQL', '内容分类']: 
            drop_view(mysql_db, view_table_names)
        

        logger.info(f'query: {query} 处理完毕')
    except Exception as e:
        logger.error(f'Unexpected error occured:{e}', exc_info=True)
        await send_to_clients(str(e) + '\n')
        await send_to_clients(json.dumps({'connect_flag': 'ERROR'}, ensure_ascii=False))
        # 执行完sql之后删除视图
        # drop_view(mysql_db, view_table_names)
        # 出现错误时，移除客户端连接
        
        clients.remove(websocket)




@app.post('/load_config', summary='加载数据源配置信息')
async def load_config(databaseId: int):

    # 获取配置信息
    mysql_db, param_db, description, client, _, unstructured_column, target_table, selected_tables, params_dict \
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
    

    config_param_dict = {}
    # 获取时间类型但是是字符串表示的字段
    datetime_str_cols = []
    if client:  # if client 等价于 if is_semantic_analysis
        first_lines = mysql_db.run(f'SELECT * FROM {target_table} LIMIT 1', include_columns=True)
        first_lines = eval(first_lines)
        for k, v in first_lines[0].items():
            if isinstance(v, str) and is_valid_datetime(v):
                datetime_str_cols.append(k)

        # 只有开启语义时才会重写这部分的配置
        
        config_param_dict['large_step'] = int(params_dict['large_step'])
        config_param_dict['small_step'] = int(params_dict['small_step'])
        config_param_dict['window_size'] = int(params_dict['window_size'])
        config_param_dict['min_samples'] = int(params_dict['min_samples'])
        config_param_dict['limit'] = int(params_dict['max_samples'])

    # 重写配置
    config_param_dict['datetime_type_field'] = datetime_str_cols
    config_param_dict['columns_map'] = columns_map
    config_param_dict['unstructured_column'] = unstructured_column
    config_param_dict['is_semantic_analysis'] = 1 if client else 0
    config_param_dict['is_abbr_analysis'] = 1 if full_abbr_dict else 0 
    

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

    config_dict['table_schema_dict'].update({databaseId: table_schema_dict})
    config_dict['full_related_dict'].update({databaseId: full_related_dict})
    config_dict['full_abbr_dict'].update({databaseId: full_abbr_dict})
    config_dict['target_table'].update({databaseId: target_table})
    config_dict['unstructured_column'].update({databaseId: unstructured_column})

    config_dict['milvus_field_type'].update({databaseId: milvus_field_type})
    config_dict['milvus_opt'].update({databaseId: milvus_opt}) 
    config_dict['mysql_db'].update({databaseId: mysql_db})
    config_dict['config_param_dict'].update({databaseId: config_param_dict})
    config_dict['description'].update({databaseId: description}) 


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

