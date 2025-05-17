from pymilvus import MilvusClient
from langchain_openai import OpenAIEmbeddings
from typing import List
import numpy as np
from openai import OpenAI
from pymilvus import AnnSearchRequest
from pymilvus import RRFRanker
from pymilvus import MilvusClient
from milvus_model.sparse.bm25.bm25 import BM25EmbeddingFunction
from milvus_model.sparse.bm25.tokenizers import build_default_analyzer
import time  
from models.langchain_models import embedding_bge

class MilvusOperation(object):
    def __init__(self, uri: str, collection_name: str, bm25_ef_path: str):
        self.client = MilvusClient(uri=uri)
        self.collection_name = collection_name
        self.embedding_bge = embedding_bge
        self.dimension = self.embedding_bge(['obtain embedding dimension']).shape[-1]
        self.bm25_ef = self.bm25_init(bm25_ef_path)
        self.bm25_ef.encode_documents(['load jieba cache'])

        self.ranker = RRFRanker(100)
        

    def bm25_init(self, bm25_ef_path):
        analyzer = build_default_analyzer(language="zh")
        bm25_ef = BM25EmbeddingFunction(analyzer)
        bm25_ef.load(bm25_ef_path)

        return bm25_ef




    # 根据过滤条件查询
    def query_with_filter(self,  filter_exp='', output_fields=[], limit=5000):
        ret = self.client.query(collection_name=self.collection_name, filter=filter_exp, output_fields=output_fields, limit=limit)
        
        return [each_data for each_data in ret]   # query 似乎不支持多个查询,
        
    # 向量稠密检索
    def search_vector_filter(self, query,  filter_exp='', output_fields=[], limit=5000):
        vector = self.embedding_bge([query])

        res = self.client.search(collection_name=self.collection_name, data=vector, filter=filter_exp, limit=limit, output_fields=output_fields, )
        return res
    
    # 混合检索
    def search_hybrid(self, query: str, filter_exp: str = '', output_fields: list = [], limit: int = 5000):

        # 事项作为查询向量
        query_dense_vector = self.embedding_bge([query])[0]

        search_param_1 = {
            "data": [query_dense_vector],
            "anns_field": "dense",
            "param": {
                "metric_type": "IP",
                "params": {"nprobe": 10}
            },
            "limit": limit, 
            "expr": filter_exp
        }
        request_dense = AnnSearchRequest(**search_param_1)
        query_sparse_vector = self.bm25_ef.encode_documents([query])
        search_param_2 = {
            "data": [query_sparse_vector],
            "anns_field": "sparse",
            "param": {
                "metric_type": "IP",
                "params": {"drop_ratio_build": 0.2}
            },
            "limit": limit,
            "expr": filter_exp 
        }
        request_sparse = AnnSearchRequest(**search_param_2)
        
        reqs = [request_dense, request_sparse]

        search_result = self.client.hybrid_search(
            collection_name=self.collection_name,
            reqs=reqs,
            ranker=self.ranker,
            limit=limit,
            output_fields=output_fields
        )
        
        return search_result 




if __name__ == '__main__':


    collection_name = 'hongkou_hotline_order'
    uri = 'http://172.31.24.111:19535'

    opt = MilvusOperation(uri=uri, bm25_ef_path='hongkou_hotline_bm25.json')
    question = '统计虹口有哪些公园噪声扰民问题'
    # question = '道路积水事件'
    res = opt.search_hybrid(collection_name, 
                            query=question, 
                            filter_exp="Work_Order_Type == '求助类' and Item_Category == '公共管理'", 
                            output_fields=['Case_Description', ],
                            limit=10)
    res = res[0]
    print(res) 