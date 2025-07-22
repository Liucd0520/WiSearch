import pandas as pd 
from langchain_openai import ChatOpenAI
from langchain_core.prompts.prompt import PromptTemplate
from sklearn.cluster import DBSCAN
from BCEmbedding import EmbeddingModel    
from collections import defaultdict
from collections import OrderedDict
import numpy as np 


model = ChatOpenAI(model="text2sql2", #   Qwen2.5-14B
                    base_url='http://172.31.24.111:33071/v1', 
                    api_key='EMPTY',
                    temperature=0,
                    )

summary_prompt = """
# 指令
如下的工单列表反映了同一个事件主题，请根据一批工单的内容描述总结出对应的内容概要，要求在15字以内

# 要求
- 只总结反馈的内容，不要输出用户的诉求
-  格式尽可能保持 地址 + 事件 的方式

# 示例
麻将馆噪音扰民
建筑工地施工扰民及影响学生身体健康问题

# 工单列表
{order_list}

# 内容概要：

"""

prompt = PromptTemplate(template=summary_prompt, input_variables=["order_list", ])
summary_chain =  prompt | model


def dbscan_infer(embeddings, eps, min_samples):

    dbscan = DBSCAN(eps=eps, min_samples=min_samples,n_jobs=8)
    y = dbscan.fit_predict(embeddings)  # y 是每个sentence的聚类标签，与句子数目相同
    return y


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

def obtain_theme(df, embedding_model):
    result = df.groupby('label')['问题描述'].apply(list).to_dict() # {label1: order_list1, label2:orderlist2 ...}

    label2theme = build_label2theme_with_batch(result, summary_chain)

    sentence_list = list(label2theme.values())
    embeddings_sent = embedding_model.encode(sentence_list, batch_size=4,) 

    cluster_labels = dbscan_infer(embeddings_sent, 0.6, 2) # -1, -1, 0, 0, -1, -1 ...
    cluster_labels = [int(label) for label in cluster_labels]
    
    # 根据原始的标签与主题的映射变量label2theme 与 聚类后的标签cluster_labels 生成新的
    new_label2theme = update_mapping(label2theme, cluster_labels)
    
    # 使用 map() 创建新列 'theme'
    df['theme'] = df['label'].map(new_label2theme)
    
    return df



if __name__ == '__main__':
    bce_model_path = '/workspace/checkpoint-100'
    embedding_model = EmbeddingModel(model_name_or_path=bce_model_path,
            device='cuda:0'
            ) 
    df = pd.read_excel('分析结果.xlsx')
    import time
    start = time.time()
    df_postprocess = obtain_theme(df, embedding_model)
    print(time.time() - start)
    df_postprocess.to_csv('result.csv')
    

