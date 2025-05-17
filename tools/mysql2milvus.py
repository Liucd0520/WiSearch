
from pathlib import Path
import sys 
import os 
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)


import pandas as pd 
from configs import config # mysql_uri, table_names, uri, related_columns
from langchain_community.utilities import SQLDatabase
from pymilvus import MilvusClient, DataType
import pandas as pd
import time
from openai import OpenAI
import numpy as np
from milvus_model.sparse.bm25.bm25 import BM25EmbeddingFunction
from milvus_model.sparse.bm25.tokenizers import build_default_analyzer
from pymilvus import AnnSearchRequest, RRFRanker, connections, CollectionSchema, FieldSchema, DataType, Collection
from models.langchain_models import embedding_bge
from tools.utils import build_index
from tools.utils import build_schema
import datetime

unstr_field = config.related_columns[-1]
primary_key_name = config.primary_key_name

mysql_table_name = config.table_names[0]
collection_name = config.collection_name



# 连接服务器
mysql_db = SQLDatabase.from_uri(config.mysql_uri)
client = MilvusClient(uri=config.uri)



def mysql_values_operator(table_name, column_name):
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


corpus = mysql_values_operator(mysql_table_name, unstr_field)
if not os.path.exists(config.bm25_ef_path): 
    bm25_ef = sparse_embedding_gen(corpus=corpus, save_path=config.bm25_ef_path)
else:
    bm25_ef = bm25_init(config.bm25_ef_path)


schema = build_schema(mysql_db, mysql_table_name, primary_key_name)
# print(schema)

index_params = build_index(client)

client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params
    )


def obtain_data_mysql(table_name, batch_size=1000, offset=0):

    """按批次获取 MySQL 表中某列的值"""
    cmd = f'SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset};'
    values = mysql_db.run(cmd, include_columns=True)
    values_list = eval(values) if values != '' else []
    return values_list



# # ------------插入数据-------------------
batch_size = 1000
offset = 0 
while True:

    batch_data = obtain_data_mysql(mysql_table_name, batch_size=batch_size, offset=offset)
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
    batch_data = [ {config.columns_map[k]: v  for k, v in each_data.items()}  for each_data in batch_data ]
    
    text_list = [each_data[config.columns_map[unstr_field]] for each_data in batch_data]
    sparse_embs = bm25_ef.encode_documents(text_list)
    dense_embs = embedding_bge(text_list)

    insert_data = []
    for i, each_data in enumerate(batch_data):
        each_data = batch_data[i] 
        dense_emb = dense_embs[i]
        sparse_emb = sparse_embs._getrow(i)
        each_data.update({
            "sparse": sparse_emb, 
            'dense': dense_emb                         
        }) 
        insert_data.append(each_data)
    print('END')
    client.insert(collection_name=collection_name, data=insert_data)

    offset += batch_size

    break

    

