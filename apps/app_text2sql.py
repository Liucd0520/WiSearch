
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
from configs import config as config
from offline_initial_file import init
from langchain_community.utilities import SQLDatabase

from fastapi import APIRouter, FastAPI
import os
from module.prompt import *
from models.langchain_models import llm_qwen_14B
from utils.util import *
from sql_processing.text2sql import schema_linking, sql_gen
from configs import config as config
from offline_initial_file import init
from langchain_community.utilities import SQLDatabase
from module.main_llm import *
from online_sql import sql_path, sql_path_pure

import uvicorn



app = FastAPI()

@app.post('/text2sql', summary='标准的Text2sql')
async def sql_gen(query: str,):
    start = time.time()
    
    logger.info(f'query: {query}')
    
    new_linking_columns = schema_linking(query, schema, config.related_columns, distinct_values, schema_linking_samples,  schema_linking_chain)
    logger.info(f"schema linking: {new_linking_columns}")

    obtain_data, sql_result = await sql_path_pure(query, mysql_db,
                                                new_linking_columns, schema, 
                                                sql_gen_chain, sql_feedback_chain)
 
    logger.info(f"obtain_data: {obtain_data}")
    logger.info(f"sql_result: {sql_result}")    
    return {"data": obtain_data, "sql": sql_result, 'time': time.time() - start}



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
            is_distinct_values_gen=True,
            )
    schema = '\n'.join(schema_list)


    uvicorn.run(app=app, host='0.0.0.0', port=8077)

