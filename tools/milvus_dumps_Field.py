from pymilvus import MilvusClient, DataType
import pandas as pd
import time
from openai import OpenAI
import numpy as np
from milvus_model.sparse.bm25.bm25 import BM25EmbeddingFunction
from milvus_model.sparse.bm25.tokenizers import build_default_analyzer
from pymilvus import AnnSearchRequest, RRFRanker, connections, CollectionSchema, FieldSchema, DataType, Collection
import sys
import os 
# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
# 将父目录添加到 sys.path
sys.path.append(parent_dir)

from configs import config
from models.langchain_models import embedding_bge



# ---------读取文档内容--------
df = pd.read_excel('工单事件表_虹口.xlsx')
df.fillna('', inplace=True)
select_columns = list(config.columns_map.keys())
# df['发现时间'] = df['发现时间'].dt.strftime('%Y%m%d%H%M%S')
# df['收单时间'] = df['收单时间'].dt.strftime('%Y%m%d%H%M%S')
# df['派遣时间'] = df['派遣时间'].dt.strftime('%Y%m%d%H%M%S')


df_new = df[select_columns]
df_new.rename(columns=config.columns_map, inplace=True)
data_list = df_new.to_dict('records')
print(data_list[0])

# ----------定义稀疏Embedding模型------------
corpus = [each_data['Case_Description'] for each_data in data_list]
analyzer = build_default_analyzer(language="zh")
bm25_ef = BM25EmbeddingFunction(analyzer)
bm25_ef.fit(corpus)
bm25_ef.save('hongkou_hotline_bm25.json')




client = MilvusClient(uri=config.uri)

# Create schema
schema = MilvusClient.create_schema(
    auto_id=False,
    enable_dynamic_field=True,
)

# Add fields to schema
schema.add_field(field_name="Case_ID", datatype=DataType.INT64, is_primary=True)
schema.add_field(field_name="Original_ID", datatype=DataType.INT64, )
schema.add_field(field_name="Case_Source", datatype=DataType.VARCHAR, max_length=20)
schema.add_field(field_name="Work_Order_Type", datatype=DataType.VARCHAR, max_length=20)
schema.add_field(field_name="Discovery_Time", datatype=DataType.VARCHAR, max_length=20)
schema.add_field(field_name="Status", datatype=DataType.VARCHAR, max_length=20)
schema.add_field(field_name="Item_Category", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Major_Item_Category", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Minor_Item_Category", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Item_Name", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Item_Tag", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Case_Description", datatype=DataType.VARCHAR, max_length=10000)
schema.add_field(field_name="Reported_Address", datatype=DataType.VARCHAR, max_length=1000)
schema.add_field(field_name="Actual_Address", datatype=DataType.VARCHAR, max_length=1000 )
schema.add_field(field_name="Contact_Person", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Contact_Number", datatype=DataType.VARCHAR, max_length=11)
schema.add_field(field_name="Street_Affiliation", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Primary_Department", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Collaborative_Department", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Primary_Disposal_Department", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Collaborative_Disposal_Department", datatype=DataType.VARCHAR, max_length=500)
schema.add_field(field_name="Handling_Description", datatype=DataType.VARCHAR, max_length=10000)

schema.add_field(field_name="Closure_Time", datatype=DataType.VARCHAR, max_length=20)
schema.add_field(field_name="Closure_Deadline_Overdue", datatype=DataType.VARCHAR, max_length=10)
schema.add_field(field_name="City_Urgency_Level", datatype=DataType.VARCHAR, max_length=10)
schema.add_field(field_name="Receiving_Time", datatype=DataType.VARCHAR, max_length=20)
schema.add_field(field_name="Urgency_Level", datatype=DataType.VARCHAR, max_length=14)
schema.add_field(field_name="Area_Affiliation", datatype=DataType.VARCHAR, max_length=100)

schema.add_field(field_name="Community_Committee_Affiliation", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Dispatch_Time", datatype=DataType.VARCHAR, max_length=20)
schema.add_field(field_name="Case_Deadline", datatype=DataType.INT16, max_length=50)

schema.add_field(field_name="Disposal_Timer", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Overall_Case_Timer", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Fact_Recognition", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Request_Recognition", datatype=DataType.VARCHAR, max_length=100)

schema.add_field(field_name="Is_Zone_Follow_Up_Solved", datatype=DataType.VARCHAR, max_length=100)
schema.add_field(field_name="Is_Zone_Follow_Up_Satisfied", datatype=DataType.VARCHAR, max_length=100)

schema.add_field(field_name="sparse", datatype=DataType.SPARSE_FLOAT_VECTOR)
schema.add_field(field_name="dense", datatype=DataType.FLOAT_VECTOR, dim=1024)   # dim: 


# Prepare index parameters
index_params = client.prepare_index_params()

# Add indexes
index_params.add_index(
    field_name="dense",
    index_name="dense_index",
    index_type="IVF_FLAT",
    metric_type="IP",
    params={"nlist": 128},
)

index_params.add_index(
    field_name="sparse",
    index_name="sparse_index",
    index_type="SPARSE_INVERTED_INDEX",  # Index type for sparse vectors
    metric_type="IP",  # Currently, only IP (Inner Product) is supported for sparse vectors
    params={"drop_ratio_build": 0.2},  # The ratio of small vector values to be dropped during indexing
)


client.create_collection(
    collection_name=config.collection_name,
    schema=schema,
    index_params=index_params
)




# ------------插入数据-------------------
batch_size = 1000
print(len(data_list)//batch_size + 1)

for idx in range(0, len(data_list)//batch_size + 1):
    print(idx)
    batch_data = data_list[batch_size * idx: (1+idx) * batch_size]
    
    text_list = [each_data['Case_Description'] for each_data in batch_data]
    print('xxxxxxxxxxx')
    sparse_embs = bm25_ef.encode_documents(text_list)
    dense_embs = embedding_bge(text_list)
    print('===============')
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

    
    client.insert(collection_name=config.collection_name, data=insert_data)



