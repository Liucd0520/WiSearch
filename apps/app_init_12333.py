from pathlib import Path
import sys 
import os 
import json
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)


from fastapi import FastAPI, APIRouter
from offline_initial_db import init_db
from module.main_llm import meta_data_model
from models.langchain_models import llm_qwen_14B
import uvicorn
from configs import config
from pydantic import BaseModel
from typing import List
from fastapi import Body


router = FastAPI()



print(llm_qwen_14B.invoke("你好"))
meta_data_chain = meta_data_model(llm_qwen_14B)


class InitProjectItem(BaseModel):
    tableName: str = 'hongkou'
    fieldName: str = '案件编号'
    fieldType: str = 'varchar'
    fieldComment: str = 'xxxxxxxxxxxx'
    dataExample: str = '1234567890'
    isSearchDim: bool = True
    # 其他字段可以继续添加

class InitProjectRequest(BaseModel):
    data: List[InitProjectItem]


@router.post('/MetaDataGen', summary='初始化项目')
async def init_project(request: InitProjectRequest):
    data = [item.dict() for item in request.data]
    print(data)
    table_name = data[0]['tableName']
    if table_name not in config.table_names:
        return {"error": "表名不存在"}
    
    schema_list, _, distinct_values = init_db(table_names=[table_name], query_list=[], meta_data_chain=meta_data_chain, is_meta_data=True, is_schema_linking_gen=False, is_distinct_values_gen=True)
    schema = schema_list[0]
    search_dim_list = list(distinct_values.keys())
    print('搜索列表：', search_dim_list)

    columns_list = schema.split('\n')
    used_meta_columns = [] #[each_col for each_col in columns_list for  if ]
    for each_col in columns_list:
        for d_col in data:
            if f"`{d_col['fieldName']}`" in each_col:
                used_meta_columns.append(each_col)
                

    print('使用的元数据:', used_meta_columns)



    # for d_col in data: # data -> requst.data 
    #     for column_str in columns_list: # columns_list --> schema.split('\n')
    #         if f"`{d_col['fieldName']}`" in column_str:
    #             col_info = column_str.split(';')
    #             if len(col_info) != 3:  # 如果列信息不是3个，则跳过
    #                 break 
    #             else:
    #                 col_name_info, descrip, value = col_info
                    
    #                 d_col['fieldComment'] = descrip.replace('含义:', '')
    #                 d_col['dataExample'] = value
    #                 # 判断是否是关联搜索维度
    #                 for search_dim in search_dim_list:
    #                     if search_dim in col_name_info:
    #                         d_col['isSearchDim'] = True
    #                         break
    #                     else:
    #                         d_col['isSearchDim'] = False
    #             break
    #         else:
    #             print('error', f"`{d_col['fieldName']}`",  column_str)
    #             break 


    return data 

if __name__ == "__main__":
    uvicorn.run(router, host="0.0.0.0", port=8000)