
from pathlib import Path
import sys 
import os 
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from configs import config # mysql_uri, table_names, uri, related_columns
from langchain_community.utilities import SQLDatabase

import pandas as pd
import time
from openai import OpenAI
import numpy as np
from milvus_model.sparse.bm25.bm25 import BM25EmbeddingFunction
from milvus_model.sparse.bm25.tokenizers import build_default_analyzer

from models.langchain_models import embedding_bge
from tools.tool_utils import build_index
from tools.tool_utils import build_schema
import datetime
from utils.util import params_parser, decrypt, obtain_database_config
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from typing import Optional



# 表里需添加table_name
class InitProjectItem(BaseModel):
    fieldId: int = 1
    tableId: int = 1
    tableName: Optional[str] = 'hongkou'
    fieldName: Optional[str] = '案件编号'
    fieldType: Optional[str] = None
    fieldComment: Optional[str] = None 
    dataExample: Optional[str] = None
    # isSearchDim: Optional[bool] = None  # 只允许其中一个表有
    # isAbbrDim: Optional[bool] = None
    nglishName: Optional[str] = None 

    # 其他字段可以继续添加

app = FastAPI()

def mysql_values_operator(mysql_db, table_name, column_name):
    """获取非结构化字段的值"""
    
    cmd = f'SELECT DISTINCT `{column_name}` FROM {table_name};'
    values = mysql_db.run(cmd)
    values_list = eval(values) if values != '' else [{}]

    return [value[0] for value in values_list]


def sparse_embedding_gen(corpus, save_path=''):

    analyzer = build_default_analyzer(language="zh")
    bm25_ef = BM25EmbeddingFunction(analyzer)
    # corpus = [i for i in corpus if i is not None]

    bm25_ef.fit(corpus)
    bm25_ef.save(save_path)
    return bm25_ef 


def bm25_init(bm25_ef_path):
    analyzer = build_default_analyzer(language="zh")
    bm25_ef = BM25EmbeddingFunction(analyzer)
    bm25_ef.load(bm25_ef_path)

    return bm25_ef


def obtain_data_mysql(mysql_db, table_name, batch_size=1000, offset=0):

    """按批次获取 MySQL 表中某列的值"""
    cmd = f'SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset};'
    values = mysql_db.run(cmd, include_columns=True)
    values_list = eval(values) if values != '' else []
    return values_list



@app.post('/milvus_dump', summary='向量灌库')
async def vector_dump(db_id: int):
    
    if not os.path.exists(config.data_save_dir):
        os.mkdir(config.data_save_dir)

    param_uri = config.param_uri
    milvus_uri = config.milvus_uri 

    # 获取配置信息
    param_uri = config.param_uri
    mysql_db, param_db, client, primary_key_name, unstr_field, dumped_table_name, _, _ = obtain_database_config(param_uri, milvus_uri, db_id,)

    # 向量库的collection名字
    collection_name = dumped_table_name

    # 获取某个表的元数据获取
    _, _, _, columns_map = \
        params_parser(param_db, 'field_metadata', dumped_table_name)

    # 稀疏向量化
    corpus = mysql_values_operator(mysql_db, dumped_table_name, unstr_field)
    bm25_ef_path = os.path.join(config.data_save_dir, f'{collection_name}.json')
    if not os.path.exists(bm25_ef_path): 
        bm25_ef = sparse_embedding_gen(corpus=corpus, save_path=bm25_ef_path)
    else:
        bm25_ef = bm25_init(bm25_ef_path)

    schema = build_schema(mysql_db, dumped_table_name, primary_key_name, columns_map)

    index_params = build_index(client)

    if collection_name in client.list_collections():
        client.drop_collection(collection_name=collection_name)

    client.create_collection( 
            collection_name=collection_name,
            schema=schema,
            index_params=index_params
        )

    # # ------------插入数据-------------------
    batch_size = 1000
    offset = 0 
    while True:
        batch_data = obtain_data_mysql(mysql_db, dumped_table_name, batch_size=batch_size, offset=offset)
        if not batch_data:
            break

        print(batch_data[0])

        # 处理时间字段
        for each_data in batch_data: 
            # {'工单编号': 20240101000072, '工单生成时间': datetime.datetime(2024, 1, 1, 0, 37, 39), ...}
            for key, value in each_data.items():
                if isinstance(value, datetime.datetime):
                    each_data[key] = value.strftime("%Y-%m-%d %H:%M:%S")
        
        # 将字段名映射为Milvus字段名
        batch_data = [ {columns_map[k]: v  for k, v in each_data.items()}  for each_data in batch_data ]
        
        text_list = [each_data[columns_map[unstr_field]] for each_data in batch_data]
        sparse_embs = bm25_ef.encode_documents(text_list)
        dense_embs = embedding_bge(text_list)
        print(sparse_embs.shape)
        print(dense_embs.shape)
        print(len(batch_data))
        
        unstructured_col_milvus = columns_map[unstr_field]
        print(unstructured_col_milvus)
        insert_data = []
        for i, each_data in enumerate(batch_data):
            each_data = batch_data[i] 
            dense_emb = dense_embs[i]
            sparse_emb = sparse_embs._getrow(i)
            each_data.update({
                "sparse": sparse_emb, 
                'dense': dense_emb,
                unstructured_col_milvus: each_data[unstructured_col_milvus] if  each_data[unstructured_col_milvus]  else ''                  
            }) 
            insert_data.append(each_data)
        print(insert_data[0])
        client.insert(collection_name=collection_name, data=insert_data)

        offset += batch_size



# 获取当前入库进度
@app.post('/milvus_timeline', summary='灌库进度')
async def dump_timeline(db_id: int):
    
    param_uri = config.param_uri
    milvus_uri = config.milvus_uri 

    # 获取配置信息
    mysql_db, _, client, _, unstr_field, dumped_table_name, _, _ = obtain_database_config(param_uri, milvus_uri, db_id)
    mysql_res = mysql_db.run(f'SELECT COUNT(DISTINCT `{unstr_field}`) AS total_num FROM {dumped_table_name}', include_columns=True)
    total_num = eval(mysql_res)[0]['total_num']
    # 向量库的collection名字
    collection_name = dumped_table_name
    if collection_name in client.list_collections():
        milvus_res = client.query(
        collection_name=collection_name, 
        output_fields=["count(*)"]
        )
        current_num = milvus_res[0]['count(*)']
    else:
        current_num = 0

    return round(current_num / total_num)
    

if __name__ == '__main__':
    
    uvicorn.run(app=app, host='0.0.0.0', port=8078,) 


