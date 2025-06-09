from module.prompt import *

from utils.util import *
from langchain.prompts import PromptTemplate
from sql_processing.text2sql import schema_linking, sql_gen
from sql_processing.view_manager import create_temp_view, sql_replace_view, drop_view
from configs import config as config
from offline_initial_file import init
from langchain_community.utilities import SQLDatabase

from utils.util import generation_filter_expr
from operator_workflow.workflow import app_retrieve, app_retrieve_extraction, app_retrieve_summary
from online_sql import sql_path
from pymilvus import MilvusClient
from operator_workflow.milvus_client import MilvusOperation
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from apps.websocket_manager import clients
from apps.websocket_manager import send_to_clients
import json 
import uvicorn
from webui_models.utils import query_insight_generator, obtain_detail_data
from models.create_chain import * 
import simplejson

app = FastAPI()

app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
) # 中间件白名单


class ObtainDataItem(BaseModel):
    query: str = '近1年哪些小区有设备维修的需求'

# WebSocket路由
@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    clients.append(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            print(message)
            data = json.loads(message)
            # 使用 Pydantic 模型验证输入
            validated_data = ObtainDataItem(**data)
            query = validated_data.query
            view_values = '' # 暂且不设置视图


            # top_indices = retrieve_cases(query=query, embedding_corpus=embedding_corpus)
            # select_case_list = [corpus[i]  for i in top_indices]
            # filtered_list = [str(item) for item in examples if item['query'] in select_case_list] 

            
            new_linking_columns = schema_linking(query, schema, config.related_columns, distinct_values, schema_linking_samples,  schema_linking_chain)
            logger.info(f"schema linking: {new_linking_columns}")

            target_columns = new_linking_columns['target_columns']
            condition_columns = new_linking_columns['condition_columns']
            
            # 调用流式生成器并实时传输数据
            async for chunk in query_insight_generator(explanation_chain, query, schema, columns_dict):
                # logger.info(chunk)
                await websocket.send_text(chunk)  # 将每个 chunk 发送给客户端
            # chunks = []
            # async for chunk in explanation_chain.astream({ 
            #     "query": query, "schema": schema, "columns_dict": columns_dict}):
            #     chunks.append(chunk)
            #     await websocket.send_text(chunk)
                
            task_type = 'SQL'
            # 判断查询列是否在结构化字段里
            if  config.related_columns[-1] in target_columns: 
                # 意味着可能需要语义分析
                res = task_aware_chain.invoke({'query': query, })
                task_type = res['TaskType']
            logger.info(f'任务类型: {task_type}')

            if task_type in ['SQL', '内容分类']: 
            
                obtain_data, sql_result, params = await sql_path(query, new_linking_columns, schema, view_values, config.related_columns[-1],
                        sql_gen_chain, ner_clf_chain, sql_feedback_chain, app_retrieve, milvus_opt)
                # 将生成的候选sql 查询语句发生给前端
                try:
                    await send_to_clients(json.dumps({"sql_gen": sql_result['sql_std']}, ensure_ascii=False))
                except Exception as e:
                    logger.info(f'sql_gen 发送失败: {e}')
                
            elif task_type in ['内容抽取', '内容总结']:
                # 生成filter_exp (会过滤掉非结构化字段)
                filter_expr, unstructrued_value = generation_filter_expr(milvus_field_type, condition_columns, config.related_columns[-1], 
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
            try:    
                await send_to_clients(json.dumps({"response": obtain_data}, ensure_ascii=False))
            except Exception as e:
                logger.info(f'response 发送失败: {e}')

            # 获取数据明细
            # 将与结果相关的数据明细发送给前端
            if task_type in ['SQL', '内容分类']:
                pattern = r"(?i)(SELECT\s+)(.*?)(\s+FROM)"
                modified_sql = re.sub(pattern, lambda match: f"{match.group(1)}*{match.group(3)}", sql_result['sql_view'], flags=re.IGNORECASE)
                execute_result = sql_execute(config.mysql_uri, modified_sql, schema, params, sql_feedback_chain)
                result_detail = eval(execute_result) if  execute_result != '' else [{}]
            else: 
                result_detail = [{}] 
            try:
                await send_to_clients(simplejson.dumps({"data_detail": result_detail}, 
                                                default=str,ensure_ascii=False))  # 会把datatime转成字符串，另外一种是把result_detail转换字符串: str(result_detail)
            except Exception as e:
                logger.info(f'data_detail 发送失败: {e}')
    
            # 将对结果的解读发送给前端
            result_insight = chat_chain.invoke({ "query": query, "obtain_data": obtain_data})
            try:
                await send_to_clients(json.dumps( {"result_insight": result_insight}, ensure_ascii=False))
            except Exception as e:
                logger.info(f'result_insight 发送失败: {e}')

            # 将接下来的推荐问题发生给前端
            query_recommands = recommand_chain.invoke({ "query": query, "schema": schema, "obtain_data": obtain_data})
            try:    
                await send_to_clients(json.dumps({"result_recommand": query_recommands}, ensure_ascii=False))
            except Exception as e:
                logger.info(f'result_recommand 发送失败: {e}')
            
    except Exception:
        # 出现错误时，移除客户端连接
        clients.remove(websocket)




if __name__ == "__main__":

    # 初始化数据库
    milvus_opt = MilvusOperation(uri=config.uri,collection_name= config.collection_name, bm25_ef_path=config.bm25_ef_path)
    client = MilvusClient(uri=config.uri)
    collection_info = client.describe_collection(collection_name=config.collection_name)
    # 'fields': [{'field_id': 100, 'name': 'id', 'description': '', 'type': <DataType.INT64: 5>, 'params': {}, 'is_primary': True}, ]
    milvus_field_type = {each_field['name']: each_field['type'].name for each_field in collection_info['fields']} # <DataType.INT64: 5> ==> .name, .value 获取枚举类型的数据
    # {'id': 'INT64'}

    mysql_db = SQLDatabase.from_uri(config.mysql_uri)

    # 获取所有选定表的字段名
    columns_dict = {}
    for table_name in config.table_names:
        table_info = eval(mysql_db.run(f"SHOW COLUMNS FROM {table_name};"))
        columns = [items[0] for items in table_info]
        columns_dict[table_name] = columns


    if not os.path.exists(config.data_save_dir):
        os.makedirs(config.data_save_dir)
    if not os.path.exists(config.log_dir):
        os.makedirs(config.log_dir)
    
    gen_query_list = ['查询2024年公共管理事项的工单数量',
                    "查询物业收费事件的工单类型分布",
                    "查询2024年台风相关工单随月份的变化趋势" 
                ]
    setup_flag = False
    schema_list, schema_linking_samples, distinct_values = \
        init(query_list=gen_query_list, 
            is_meta_data=setup_flag, 
            is_schema_linking_gen=setup_flag, 
            is_distinct_values_gen=setup_flag)
    schema = '\n'.join(schema_list)

    

    uvicorn.run(app=app, host='0.0.0.0', port=33064)


