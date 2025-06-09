import requests 
from langchain_community.utilities import SQLDatabase
from configs import config
from sqlalchemy import create_engine
import pandas as pd

# # 表里需添加table_name
# class InitProjectItem(BaseModel):
#     tableName: str = 'hongkou'
#     fieldName: str = '案件编号'
#     fieldType: str = 'varchar'
#     fieldComment: str = ''
#     dataExample: str = '示例值：1234567890'
#     isSearchDim: bool = False
#     isAbbrDim: bool = False 
#     EnglishName: str = ''



mysql_db = SQLDatabase.from_uri(config.mysql_uri,sample_rows_in_table_info=0)
table_info = mysql_db.get_table_info(table_names=config.data_table_names)
field_info = table_info.split('\n')[2: -2]
field_name_list = [i.split(' ')[0].strip() for i in field_info]
field_comment_list = [i.split('COMMENT')[-1] for i in field_info]
field_type_list = [i.split(' ')[1].lower().split('(')[0] for i in field_info]


data = []
for field_name,filed_type, field_comment in zip(field_name_list,field_type_list, field_comment_list):
    data.append({
        'filedID': 0,
        'tableID': 0,   
        "tableName": config.data_table_names[0],
        "fieldName": field_name,
        "fieldType": filed_type,
        "fieldComment": field_comment,
        "dataExample": '',
        "isSearchDim": False,
        "isAbbrDim": False,
        "EnglishName": ''
    })
print(data)
url = 'http://localhost:8077/MetaDataGen'
result = requests.post(url=url, json={'data': data})
print(result.json())

schema_list = []
start_str = f"CREATE TABLE `{config.data_table_names[0]}` ("
schema_list.append(start_str)
for field_meta_data in result.json()['data']:
    meta_data_str = f"""`{field_meta_data['fieldName']}` {field_meta_data['fieldType']}; {field_meta_data['fieldComment']}; {field_meta_data['dataExample']}"""
    schema_list.append(meta_data_str)
end_str = f""") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci """

schema_list.append(end_str)
schema = '\n'.join(schema_list)
print(schema)

