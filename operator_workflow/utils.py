
from sklearn.cluster import DBSCAN, KMeans
import numpy as np 
from models.langchain_models import embedding_bge
from operator_workflow.milvus_client import MilvusOperation
from configs import config 
from collections import Counter
from langchain.schema.runnable import Runnable
from utils.util import * 
from configs import config 
from collections import OrderedDict

### 尽量添加关键词，协助搜索，这个关键词未必是query里面有的，可以是让大模型自己生成的
def retrieve_document_milvus(query: str, milvus_opt: object,  filter_exp='', limit=5000):
    """query 是非结构化内容"""
    
    unstructured_field = config.columns_map[config.unstructured_column] 

    if query: # query 非空        
        search_result = milvus_opt.search_hybrid(
            query=query, 
            output_fields=[unstructured_field, 'dense'],  # 除了`内容描述`之外选择使用哪些字段应该由query解析的结果决定
            filter_exp=filter_exp, 
            limit = limit)
        result = search_result[0]  # 因为query只有一个，而milvus支持若干个
        
        return [retr_result['entity'][unstructured_field] for retr_result in result], \
               [retr_result['entity']['dense'] for retr_result in result]
    
    else: 
        search_result = milvus_opt.query_with_filter(
            output_fields=[unstructured_field, 'dense'],  # 除了`内容描述`之外选择使用哪些字段应该由query解析的结果决定
            filter_exp=filter_exp, 
            limit = limit)
       
        return [retr_result[unstructured_field] for retr_result in search_result], \
                [retr_result['dense'] for retr_result in search_result]
        



async def index_search(query: str, documents: list, grade_chain: Runnable):

    large_step = config.large_step
    small_step = config.small_step

    overlap = 2  # 列表之间有3个元素的重叠，免得切分导致把3个连续的[no, no, no] 划分成两块，从而miss
    find_flag = 0

    for i in range(0, len(documents) - large_step + 1, large_step-overlap):
        # 以200个为一簇的子文档
        sub_documents = documents[i: i+large_step]  
        # 分层采样
        steped_documents = [sub_documents[i] for i in range(0, len(sub_documents), small_step)]

        step_scores = grade_chain.batch([{"document": doc, "query": query} for doc in steped_documents], )
        logger.info(f'step_scores: {step_scores}')
        
        for step_score, steped_doc in zip(step_scores, steped_documents):
            logger.info(f'层级抽取文档： {steped_doc} ==> {step_score}  ' )

        # 按照连续三个为no则截断的规则获取前K个
        for idx in range(0, len(step_scores)-2, ):
            if step_scores[idx] == 'no' and step_scores[idx+1] == 'no' and step_scores[idx+2] == 'no':
                find_flag = 1
                break
        # idx 是开始为[no, no, no] 的第一个no的索引
        if find_flag == 1: # 说明找到了
            res = (i + idx * small_step) if (i + idx * small_step) != 0 else small_step
            return res

    return len(documents) -1 




def kmeans_infer(embeddings, num_cluster):
    
    kmeans = KMeans(n_clusters=num_cluster)
    kmeans.fit(embeddings)
    
    return kmeans.labels_


def dbscan_infer(embeddings, eps, min_samples):
     
    dbscan = DBSCAN(eps=eps, min_samples=min_samples,n_jobs=8)
    y = dbscan.fit_predict(embeddings)  # y 是每个sentence的聚类标签，与句子数目相同
    return y


def search_best_cluster(embeddings,  min_samples, eps_list=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8],):

    max_cluster_center = -1
    
    # 使用多次聚类，找到类别聚类中心最多的那个eps
    for eps in eps_list:
        
        temp_cluster_label = dbscan_infer(embeddings, eps, min_samples)
        
        # 统计每个元素出现的次数
        element_counts = Counter(temp_cluster_label)
        # 使用列表推导式替换符合条件的元素
        temp_cluster_label = [-1 if element_counts[x] < min_samples else x for x in temp_cluster_label]
        print('eps: ', eps, 'num_cluster', max(temp_cluster_label))
        # 保存最多的cluster_label
        if max(temp_cluster_label) >= max_cluster_center:
            max_cluster_center = max(temp_cluster_label)
            cluster_label = temp_cluster_label
       
    return cluster_label

def unstr_cluster(docs_list, dense_emb):
    """
    对docs 进行聚类操作
    """

    # labels = kmeans_infer(embeddings, num_cluster=3)
    # labels = dbscan_infer(embeddings=embeddings, eps=0.7, min_samples=2)
    labels = search_best_cluster(dense_emb, min_samples=config.min_samples)
    
    # 聚类事件分组, 会按照标签从-1 --> 最大 的顺序进行分组，第一个是噪声
    grouped = [([event for event, lable in zip(docs_list, labels) if lable == i], int(count)) for i, count in zip(*np.unique(labels, return_counts=True))]

    return grouped




def search_best_cluster_combine(embedding_theme, embedding_addr, eps, alpha_list=[0.3, 1.3], steps=10):
    
    min_samples = config.min_samples
    cluster_label = [-1] * len(embedding_theme)
    max_cluster_center = -1
    # 使用多次聚类，找到类别聚类中心最多的那个eps
    for alpha in np.linspace(alpha_list[0], alpha_list[1], steps):
        embeddings = np.hstack([embedding_theme, alpha * embedding_addr])
        temp_cluster_label = dbscan_infer(embeddings, eps, min_samples)

        # 统计每个元素出现的次数
        element_counts = Counter(temp_cluster_label)
        # 使用列表推导式替换符合条件的元素
        temp_cluster_label = [-1 if element_counts[x] < config.min_samples else x for x in temp_cluster_label]
        print('alpha: ', alpha, 'num_cluster', max(temp_cluster_label))
        
        # 保存最多的cluster_label
        if max(temp_cluster_label) > max_cluster_center:
            max_cluster_center = max(temp_cluster_label)
            cluster_label = temp_cluster_label

    return [int(label) for label in cluster_label]   


def update_mapping(label2theme, cluster_label):
    ordered_dict = OrderedDict(label2theme) # 先转换为有序字典
    for label  in np.unique(cluster_label):
        if label == -1:
            continue
        indices = [i for i, lab in enumerate(cluster_label) if lab == label] # e.g  [0, 1, 4]
        
        # 获取第一个位置的 KV 对作为标准
        first_index = indices[0]
        first_key, first_value = list(ordered_dict.items())[first_index]

        # 遍历指定索引，替换对应的 KV 对
        for i in indices:
            key_at_i = list(ordered_dict.keys())[i]
            ordered_dict[key_at_i] = first_value
        
    return dict(ordered_dict)


# 假设 summary_chain 是一个支持 batch 方法的对象

def prepare_batch_requests(result):
    batch_inputs = []
    labels_for_batch = []

    for label, order_list in result.items():
        if label == -1:
            continue  # 跳过不需要处理的 -1 标签
        
        # 准备每个请求的数据
        input_data = {"order_list": order_list[:10]}
        batch_inputs.append(input_data)
        labels_for_batch.append(label)

    return batch_inputs, labels_for_batch

def build_label2theme_with_batch(result, summary_chain):
    # 准备批量请求的数据
    batch_inputs, labels_for_batch = prepare_batch_requests(result)
    
    # 使用 batch 方法进行处理
    batch_results = summary_chain.batch(batch_inputs)  # 假设 chain 支持 batch 方法
    
    # 创建 label 到 theme 的映射
    label2theme = {-1: ""}
    for label, theme in zip(labels_for_batch, batch_results):
        label2theme[label] = theme.content  # 假设 batch 返回的结果有 content 属性

    return label2theme