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



param_db = SQLDatabase.from_uri(config.param_uri,)
param_table_name = config.param_table_metadata
data_table_name = config.data_table_names[0]
sql_cmd = f"""SELECT * FROM `{param_table_name}` """
result = param_db.run(sql_cmd,include_columns=False)  
result = eval(result)
print(result)
data = []
for item in result:
    data.append({
        'filedID': item[0],
        'tableID': item[1],   
        "tableName": item[2],
        "fieldName": item[3],
        "fieldType": item[4],
        "fieldComment": item[5],
        "dataExample": item[6],
        "isSearchDim": item[7],
        "isAbbrDim": item[8],
        "EnglishName": item[9]
    })
print(data)
url = 'http://localhost:8077/MetaDataGen'
result = requests.post(url=url, json={'data': data})

df = pd.DataFrame(result.json()['data'])
engine = create_engine(config.param_uri)

df.to_sql(name=param_table_name, con=engine, if_exists='replace', index=False)