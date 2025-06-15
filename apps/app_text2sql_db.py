
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
from langchain_community.utilities import SQLDatabase

from fastapi import APIRouter, FastAPI
import os
from module.prompt import *
from models.langchain_models import llm_qwen_14B
from utils.util import *
from sql_processing.text2sql import schema_linking, sql_gen
from configs import config as config
from langchain_community.utilities import SQLDatabase
from module.main_llm import *
from online_sql import sql_path, sql_path_pure
from models.create_chain import *
import uvicorn

 

app = FastAPI()

@app.post('/text2sql', summary='标准的Text2sql')
async def sql_gen(query: str,):
    start = time.time()
    view_values = ''
    logger.info(f'query: {query}')
    
    new_linking_columns = schema_linking(query, schema, related_columns, distinct_values, 
                                         examples={}, chain=schema_linking_chain)
    logger.info(f"schema linking: {new_linking_columns}")

    obtain_data, sql_result, params = await sql_path(query, mysql_db, new_linking_columns, schema, view_values, 
            sql_gen_chain,  sql_feedback_chain, abbr_columns[0], full_abbr_values
            )
    
    logger.info(f"obtain_data: {obtain_data}")
    logger.info(f"sql_result: {sql_result}")    
    return {"data": obtain_data, "sql": sql_result, 'time': time.time() - start}



if __name__ == '__main__':
    
    
    mysql_db = SQLDatabase.from_uri(config.mysql_uri)
    param_db = SQLDatabase.from_uri(config.param_uri)

    if not os.path.exists(config.data_save_dir):
        os.makedirs(config.data_save_dir)
    if not os.path.exists(config.log_dir):
        os.makedirs(config.log_dir)
    
    gen_query_list = []
    
    # 获取某个表的元数据获取
    schema, abbr_columns, related_columns, field_mapping = \
        params_parser(param_db, config.param_table_metadata, config.data_table_names[0])
    
    # 获取关联字段的值
    search_table_name = config.param_table_search
    distinct_values, _ = get_enum_values(param_db, search_table_name, config.max_distinct_values_num, config.max_combined_values_length)
    print(distinct_values)

    # 获取缩写列的所有枚举值
    abbr_table_name = config.param_table_abbr
    full_abbr_dict, _ = get_enum_values(param_db, abbr_table_name, 10000, 100000)
    print(full_abbr_dict)
    full_abbr_values = list(full_abbr_dict.values())[0]  # !!!!!!!!!! 仅为一个

    uvicorn.run(app=app, host='0.0.0.0', port=8077)

