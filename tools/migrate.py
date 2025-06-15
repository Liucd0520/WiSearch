
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
from tools.tool_utils import build_index
from tools.tool_utils import build_schema
import datetime
from utils.util import params_parser
import schedule
import pickle


unstr_field = config.unstructrued_column
primary_key_name = config.primary_key_name

mysql_table_name = config.data_table_names[0]
collection_name = config.collection_name


# 连接服务器
mysql_db = SQLDatabase.from_uri(config.mysql_uri)
param_db = SQLDatabase.from_uri(config.param_uri)
client = MilvusClient(uri=config.uri)

# 记录上次迁移结束时间的文件
LAST_MIGRATED_TIME_FILE = os.path.join(project_root, "last_migrated_time.pkl")
first_time_str = '2024-12-09 08:34:23'  # 该时间是前面milvus_dumps_Feild.py 数据保存后的最新时间
timestamp_field = '工单生成时间'


 # 获取某个表的元数据获取
_, _, _, columns_map = \
    params_parser(param_db, config.param_table_metadata, config.data_table_names[0])
# columns_map = config.columns_map


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



def obtain_data_mysql(table_name, batch_size=1000, offset=0):

    """按批次获取 MySQL 表中某列的值"""
    cmd = f'SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset};'
    values = mysql_db.run(cmd, include_columns=True)
    values_list = eval(values) if values != '' else []
    return values_list




corpus = mysql_values_operator(mysql_table_name, unstr_field)
if not os.path.exists(config.bm25_ef_path): 
    bm25_ef = sparse_embedding_gen(corpus=corpus, save_path=config.bm25_ef_path)
else:
    bm25_ef = bm25_init(config.bm25_ef_path)



schema = build_schema(mysql_db, mysql_table_name, primary_key_name, columns_map)
index_params = build_index(client)

client.create_collection( 
        collection_name=collection_name,
        schema=schema,
        index_params=index_params
    )


def obtain_data_by_time(table_name, since_time):
    """获取指定时间之后的数据"""
    cmd = f"SELECT * FROM {table_name} WHERE `{timestamp_field}` > '{since_time}' ORDER BY `{timestamp_field}` ASC;"
    values = mysql_db.run(cmd, include_columns=True)
    values_list = eval(values) if values != '' else []
    return values_list


def migrate_new_data_by_time():
    print("🔍 开始按时间同步新增数据...")

    # 获取上次迁移的时间
    if os.path.exists(LAST_MIGRATED_TIME_FILE):
        with open(LAST_MIGRATED_TIME_FILE, 'rb') as f:
            last_time = pickle.load(f)
    else:
        last_time = first_time_str

    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕒 上次迁移时间：{last_time}")
    print(f"🕓 当前时间：{current_time}")

    batch_data = obtain_data_by_time(mysql_table_name, since_time=last_time)

    if not batch_data:
        print("🚫 没有新增数据")
        return

    print(f"📥 正在插入 {len(batch_data)} 条新数据...")

    # 处理时间字段
    for each_data in batch_data:
        for key, value in each_data.items():
            if isinstance(value, datetime.datetime):
                each_data[key] = value.strftime("%Y-%m-%d %H:%M:%S")

    # 字段映射
    batch_data = [{columns_map[k]: v for k, v in each_data.items()} for each_data in batch_data]
    
    text_list = [each_data[columns_map[unstr_field]] for each_data in batch_data]
    sparse_embs = bm25_ef.encode_documents(text_list)
    dense_embs = embedding_bge(text_list)
    
    insert_data = []
    max_time = last_time

    for i, each_data in enumerate(batch_data):
        dense_emb = dense_embs[i]
        sparse_emb = sparse_embs._getrow(i)
    
        each_data.update({
            "sparse": sparse_emb,  # 目前版本 2.5.8;  原始是 sparse_emb.todict() 
            'dense': dense_emb
        })
        insert_data.append(each_data)

        # 更新最大时间
        current_time_str = each_data.get(columns_map[timestamp_field], None)
        if current_time_str and current_time_str > max_time:
            max_time = current_time_str

    client.insert(collection_name=collection_name, data=insert_data)

    # 保存本次迁移的最大时间
    with open(LAST_MIGRATED_TIME_FILE, 'wb') as f:
        pickle.dump(max_time, f)

    print(f"✅ 最新一条时间：{max_time}")


# 启动定时任务
if __name__ == "__main__":
    # 初始迁移（可选）
    migrate_new_data_by_time()

    # 每隔 5 分钟执行一次
    schedule.every(5).minutes.do(migrate_new_data_by_time)

    print("⏰ 定时任务已启动，每 5 分钟检查并同步新增数据...")
    while True:
        schedule.run_pending()
        time.sleep(1)