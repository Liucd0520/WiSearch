
from pathlib import Path
import sys 
import os 
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from models.langchain_models import embedding_bge

def retrieve_cases(query, corpus, top_k=3):
    """
    根据输入问题从词库中检索最相似的TOP3词条。

    参数:
        query (str): 输入的问题。
        corpus (list of str): 词库，包含多个词条。
        embedding_func (function): 嵌入模型函数，用于将文本转化为向量。

    返回:
        list of tuple: TOP3相似词条及其相似度分数。
    """
    # 将输入问题转化为向量
    print('--------')
    query_embedding = embedding_bge(query).reshape(1, -1)  # 确保是二维数组
    print(query_embedding.shape)

    corpus_embeddings = embedding_bge(corpus)
    print(corpus_embeddings.shape)

    # 计算余弦相似度
    similarities = cosine_similarity(query_embedding, corpus_embeddings).flatten()

    # 获取相似度最高的TOP3索引
    top_indices = np.argsort(similarities)[-top_k:][::-1]

    # 返回TOP3词条及其相似度分数
    return [corpus[i]  for i in top_indices]


if __name__ == "__main__":
    # 读取示例库
    case_dict = {
        "惠南分区当月一级案由数量": "SQL1",
        "陆家嘴分区当月7时到12时交通类案由数量分布": "SQL2",
        "临港分区临港新城派出所当年涉案小区数量分布": "SQL3",
        "梅园新村派出所本周福山路各案由数量分布": "SQL4",
        "外高桥分区当月报警类案由二级案由数量分布": "SQL5",
        "惠南派出所本月18日一级案由数量分布": "SQL6",
        "陆家嘴分区2024年与2023年一级案由数量比对": "SQL7",
        "外高桥分区2024年与2022年二级案由数量比对": "SQL8",
        "按照分区统计当月接警量": "SQL9",
        "陆家嘴分区2021年一级案由top10": "SQL10",
        "惠南分区2023年侵权类下各个二级案由top10": "SQL11",
        "查询分局当月所有派出所警情数top10": "SQL12",
        "查询盗窃类案由派出所警情数top10": "SQL13"        
    }
    
    query = "光明分区这个月各个一级案由的警情量有多少"
    corpus = list(case_dict.keys())

    select_case_list = retrieve_cases(query=query, corpus=corpus)
    filter_sql_samples = {case: case_dict[case] for case in select_case_list}
    print(filter_sql_samples)