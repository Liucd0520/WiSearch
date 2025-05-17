from module.prompt import *
from models.langchain_models import llm_qwen_14B
from utils.util import *
from langchain.prompts import PromptTemplate
from sql_processing.text2sql import schema_linking, sql_gen
from sql_processing.view_manager import create_temp_view, sql_replace_view, drop_view
from configs import config as config
from offline_initial_file import init
from langchain_community.utilities import SQLDatabase
from module.main_llm import *
from utils.util import generation_filter_expr
from operator_workflow.workflow import app_retrieve, app_retrieve_extraction, app_retrieve_summary
from online_sql import sql_path
from pymilvus import MilvusClient
from operator_workflow.milvus_client import MilvusOperation
import asyncio

    # select_case_list = [corpus[i]  for i in top_indices]
    # filtered_list = [str(item) for item in case_list if item['query'] in select_case_list] # 要转出str，否则后面无法Join
    # logger.info('filtered_list: {}'.format(filtered_list))
    

async def main(query, view_values):
    
    logger.info(f'query: {query}')
    
    new_linking_columns = schema_linking(query, schema, config.related_columns, distinct_values, schema_linking_samples,  schema_linking_chain)
    logger.info(f"schema linking: {new_linking_columns}")

    target_columns = new_linking_columns['target_columns']
    condition_columns = new_linking_columns['condition_columns']
    task_type = 'SQL'
     # 判断查询列是否在结构化字段里
    if  config.related_columns[-1] in target_columns: 
        # 意味着可能需要语义分析
        res = task_aware_chain.invoke({'query': query, })
        task_type = res['TaskType']
    logger.info(f'任务类型: {task_type}')

    if task_type in ['SQL', '内容分类']: 
        obtain_data, sql_result, params = await sql_path(query, new_linking_columns, schema, view_values, config.related_columns[-1],
                  sql_gen_chain, ner_clf_chain, sql_feedback_chain, 
                  app_retrieve, milvus_opt)
    
    elif task_type in ['内容抽取', '内容总结']:

        # 生成filter_exp (会过滤掉非结构化字段)
        filter_expr, unstructrued_value = generation_filter_expr(milvus_field_type, condition_columns, config.related_columns[-1], 
                                                                 ner_clf_chain, text2datetime_chain, )  
        logger.info(f'过滤表达式： {filter_expr}; 查询问题： {unstructrued_value}')
        # 执行
        if task_type == '内容总结':
            final_state = await app_retrieve_summary.ainvoke(
                {
                "unstr_value": unstructrued_value,
                "filter_exp":  filter_expr,
                "milvus_opt": milvus_opt
                }
            )
            
        elif task_type == '内容抽取':
            final_state = await app_retrieve_extraction.ainvoke(
                {
                'query': query,
                "unstr_value": unstructrued_value,
                "filter_exp":  filter_expr,
                "milvus_opt": milvus_opt
                }
            )  #  #[{"企业": "孔乙己酒家", "数量": 2}, {}, {}]
        obtain_data = final_state['outputs'] 
    else:
        print('{} 任务类型目前还不支持处理'.format(task_type))
        
    return obtain_data




if __name__ == '__main__':
    
    # 模型
    task_aware_chain = task_aware_model(llm_qwen_14B)
    schema_linking_chain = schema_linking_model(llm_qwen_14B)
    sql_gen_chain = sql_gen_model(llm_qwen_14B)
    ner_clf_chain = ner_clf_model(llm_qwen_14B)
    sql_feedback_chain = sql_feedback_model(llm_qwen_14B)
    text2datetime_chain = datetime_interval_model(llm_qwen_14B)
    meta_data_chain = meta_data_model(llm_qwen_14B)
    
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
            meta_data_chain=meta_data_chain,
            is_meta_data=setup_flag, 
            is_schema_linking_gen=setup_flag, 
            is_distinct_values_gen=setup_flag,
            )
    schema = '\n'.join(schema_list)

    

    query = '2024年8月份的工单内容中抽取出拖欠农民工工资的企业有哪些'
    view_values = ''
    import time 
    start = time.time()
    obtain_data = asyncio.run(main(query, view_values))
    print(obtain_data)
    print(time.time() - start)




