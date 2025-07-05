
import sys 
import os 
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain_community.utilities import SQLDatabase

from module.prompt import *
from utils.util import *
from typing import Dict, List

from models.create_chain import each_meta_data_chain, translate_chain
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from typing import Optional



# 表里需添加table_name
class InitProjectItem(BaseModel):
    fieldId: int = 1
    databaseId: int = 15
    tableId: int = 1
    tableName: Optional[str] = 'hongkou'
    fieldName: Optional[str] = '案件编号'
    fieldType: Optional[str] = None
    fieldComment: Optional[str] = None 
    dataExample: Optional[str] = None
    # isSearchDim: Optional[bool] = None  # 只允许其中一个表有
    # isAbbrDim: Optional[bool] = None
    englishName: Optional[str] = None 

    # 其他字段可以继续添加

class InitProjectRequest(BaseModel):
    data: List[InitProjectItem]


app = FastAPI()



@app.post('/MetaDataGen', summary='生成元数据')
async def meta_data_gen(request: InitProjectRequest):
    
    data = [item.model_dump() for item in request.data]
    table_name = data[0]['tableName']
    database_id = data[0]['databaseId']
   

    # 获取配置信息
    mysql_db, param_db, client, _, unstructured_column, dumped_table_name, selected_tables, _ \
          = obtain_database_config(config.param_uri, config.milvus_uri, db_id=database_id,)
    
    
    full_schema = mysql_db.get_table_info(table_names=[table_name],)  
    logger.info(f"full_schema: {full_schema}")

    # 获取枚举值的类型
    enum_values, sample_values = get_enum_values(mysql_db, table_name, config.max_distinct_values_num, config.max_combined_values_length)
    
    # 重新获取字段描述信息
    input_params = []
    for each_data in data:
        field_name = each_data['fieldName']
        field_type = each_data['fieldType']
        field_comment = each_data['fieldComment']
        
        each_field_enum_values = enum_values.get(field_name, [])
        field_info = f'`{field_name}` {field_type}, {field_comment}'
        input_params.append({
            'db_info': db_info,
            'full_schema': full_schema,
            'enum_values': '', # each_field_enum_values,
            'field_info': field_info
        })

    field_schema_gens = await each_meta_data_chain.abatch(input_params)       
    english_name_gens = await translate_chain.abatch([each_data['fieldName'] for each_data in data])

    # 重新组装信息
    for each_data, field_schema, english_name in zip(data, field_schema_gens, english_name_gens):
        field_name = each_data['fieldName']
        # 重新获取字段描述信息
        each_data['fieldComment'] = field_schema

        # 获取英文名
        each_data['englishName'] = english_name

        # 重新获取枚举值
        enum_value = enum_values.get(field_name, [])
        sample_value = sample_values.get(field_name, [])
        if enum_value:
            each_data['dataExample'] = '枚举值：' + ', '.join([str(i) for i in  enum_value])
            each_data['fieldType'] = 'enum'
        if sample_value:
            each_data['dataExample'] = '样例值：' + ', '.join([str(i) for i in sample_value])
        
    return {'data': data}



if __name__ == '__main__':
    
    

    db_info = '这是上海12345的热线工单系统数据库'
    
    uvicorn.run(app=app, host='0.0.0.0', port=8077,) 

