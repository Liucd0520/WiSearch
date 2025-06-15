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

from fastapi import FastAPI
# from apps.app_excel2db import router as excel2db_router
# from apps.app_init_12333 import router as init_router
from apps.app_text2sql import router as text2sql_router

import uvicorn


app = FastAPI()

# Include the routers with their respective prefixes
# app.include_router(excel2db_router, prefix="/excel2db", tags=["ChatBI-Dev"])
# app.include_router(init_router, prefix="/initial", tags=["ChatBI-Dev"])
app.include_router(text2sql_router, prefix="/obtain_data", tags=["ChatBI-Dev"])



if __name__ == '__main__':
    
    # 模型
    schema_linking_chain = schema_linking_model(llm_qwen_14B)
    sql_gen_chain = sql_gen_model(llm_qwen_14B)
    sql_feedback_chain = sql_feedback_model(llm_qwen_14B)
    meta_data_chain = meta_data_model(llm_qwen_14B)
    
    
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
    
    gen_query_list = ['上海有多少个大国工匠',
                    "上海大国工匠的岗位分布",
                    "60岁以上的大国工匠有多少人",
                    "有多少个水电工工匠",
                    "医疗领域的工匠有多少人",
                    "介绍一下沈国兴工匠"
                ]
    
    setup_flag = False   # Ture: 从0 开始生成，False: 读取文件里的
    schema_list, schema_linking_samples, distinct_values = \
        init(query_list=gen_query_list, 
            meta_data_chain=meta_data_chain,
            is_meta_data=setup_flag, 
            is_schema_linking_gen=setup_flag, 
            is_distinct_values_gen=setup_flag,
            )
    schema = '\n'.join(schema_list)


    uvicorn.run(app=app, host='0.0.0.0', port=8077)

