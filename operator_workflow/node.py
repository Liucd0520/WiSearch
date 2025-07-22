
from operator_workflow.utils import retrieve_document_milvus, unstr_cluster, build_label2theme_with_batch
from operator_workflow.utils import index_search, dbscan_infer, update_mapping
from module.structured_output import create_str_chain, create_json_chain, create_structured_chain
from langchain.prompts import PromptTemplate
from operator_workflow.prompt import *
from pydantic import BaseModel, Field
from typing import List, Literal
from configs import config 
from pymilvus import MilvusClient
from collections import Counter
from typing import List
import random 
from models.langchain_models import llm_qwen_14B, llm_qwen_7B
from utils.util import *
import numpy as np 
from more_itertools import collapse
from models.langchain_models import embedding_bge
from itertools import groupby
from operator import itemgetter
from operator_workflow.utils import search_best_cluster_combine


class KeywordExtraction(BaseModel):
    extracted_keyword: List[str] = Field(
        description="extract keyword or named entity based on query")

class ExtractTargetModel(BaseModel):
    extract_target: list # str


grade_prompt = PromptTemplate(template=create_documentgrade_prompt_template, input_variables=["document", "query"])
grade_chain = create_str_chain(grade_prompt, llm_qwen_7B)

kw_prompt = PromptTemplate(template=obtain_keyword_list_prompt, input_variables=["query",]) #  obtain_keyword_prompt
keyword_chain =  create_structured_chain(kw_prompt, llm_qwen_7B, structured_data=ExtractTargetModel)

# 单个关键词
# extraction_prompt = PromptTemplate(template=create_extraction_prompt_template, 
#                         input_variables=["key_word", "document_with_address", "query"])
# enr_ext_chain =  create_json_chain(extraction_prompt, llm_qwen_7B)
   # 获取要抽取的值
# 多个关键词
IE_prompt = PromptTemplate(template=create_extraction_list_prompt_template,
                        input_variables=["key_word_json", "document_with_address",  "query"])
enr_ext_chain =  create_json_chain(IE_prompt, llm_qwen_7B) #create_structured_chain(prompt, EntityExtraction)

summary_prompt = PromptTemplate(template=create_summary_prompt_template, input_variables=["docs_list"])
summary_chain = create_str_chain(summary_prompt, llm_qwen_7B)

simorder_prompt = PromptTemplate(template=simorder_theme_prompt, input_variables=["order_list", ])
simorder_chain =  simorder_prompt | llm_qwen_7B

# 多人同诉找地址字段的模型
prompt = PromptTemplate(template=address_find_prompt, input_variables=["schema", ])
address_find_chain = create_json_chain(prompt, llm_qwen_14B, )

async def retrieve(state):
    """
    retrieve documents from milvus
    Args:
        state (dict): The current graph state

        Returns:
            state (dict): update document based on LLM generation
    """
    logger.info('开始对非结构化文档【粗略】检索')
    
    filter_exp = state['filter_exp']
    milvus_opt = state['milvus_opt']
    unstructured_value = state['unstr_value']
    print(unstructured_value, milvus_opt, filter_exp,)
    documents, dense_emb = retrieve_document_milvus(unstructured_value, milvus_opt, filter_exp, limit=config.limit)
    logger.info(f'检索到的文档总数量为：{len(documents)}')
    
    return {"documents": documents, "outputs": np.array(dense_emb)}


class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""

    binary_score: Literal["yes", "no"] = Field(
        ...,
        description="Documents are relevant to the question, 'yes' or 'no'",
    )


async def relevance_grade(state):
    """
    Evaluate the Retrieved Documents

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): update document based on LLM generation
        """
    
    logger.info('开始对非结构化文档【深度】检索')
    unstructured_value =  state["unstr_value"]
    documents = state['documents']
    dense_emb = state['outputs']

    if unstructured_value == '': # 没有非结构化字段，是四级分类里的信息，上一步的过滤查询已经获取到了
        return {'documents': documents}

    # grade_chain.batch([{"document": doc, "query": query} for doc in steped_documents], )
    idx = await index_search(unstructured_value, documents, grade_chain)
    window_size = min(config.window_size, 100)  # 与阈值的idx有关，最多不超过100个
    logger.info(f"阈值索引为：{idx}, 窗口大小为: {window_size} ")
    accept_idx = max(0, idx - window_size + 1)
    document_accept = documents[: accept_idx]
    embedding_accept = dense_emb[: accept_idx]
    condidate_document = documents[max(0, accept_idx): idx + window_size]    #  document[:None] = document
    condidate_embeddings = dense_emb[max(0, accept_idx): idx + window_size]
    logger.info(f'确定的文档: {len(document_accept)}; 在次确认的文档: {len(condidate_document)}')

    # 对剩余的分类
    scores_list = await grade_chain.abatch([{"document": doc, 
                                            "query": unstructured_value
                                            } for doc in condidate_document], ) # f"与 <{unstructured_value}> 相关的{config.unstructrued_column}
    
    filtered_docs = []
    filtered_embs = []
    for score, d, emb in zip(scores_list, condidate_document, condidate_embeddings):
        if score == "yes":
            filtered_docs.append(d)
            filtered_embs.append(emb)

    logger.info(f'从{len(condidate_document)}个需再次确认的文档中筛选出的相关文档数量：{len(filtered_docs)}')
    logger.info(f'示例文档：{filtered_docs[-5: ]}')
    
    total_document = document_accept + filtered_docs
    total_embedding = np.vstack([embedding_accept, filtered_embs])
    
    return {'documents': total_document, "outputs": total_embedding}
    
    # step 10:  搜到104s   29s
    # step 20:  搜到137个  38s
    # full --> 209



async def ENR_with_extension(state):
    
    documents = state['documents']
    query = state['query']
    milvus_opt = state['milvus_opt']

    if len(documents) == 0:
        return {'outputs': []}

    # 识别query中要抽取的目标字段，比如“半年来偷税漏税的企业有哪些” ==》 企业
    result_keyword = keyword_chain.invoke({"query": query})
    key_words =result_keyword.extract_target if len(result_keyword.extract_target) > 0 else "抽取的信息"
    logger.info(f'抽取的关键词列表为：{key_words}')
    # 多个key_word 分别提取
    key_word_json = {kw: f"<抽取{kw}信息>" for kw in key_words}
    # # 手动构带双引号的字典
    key_word_format = "{%s}" % ", ".join(f'"{k}": "{v}"' for k, v in key_word_json.items())

    logger.info('关键词json输出格式 --> {}'.format(key_word_format))


    unstr_filed = config.unstructured_column
    unstr_field_en = config.columns_map[unstr_filed]  # 向量数据库中的非结构化字段的英文列名
    extend_field_en = config.columns_map[config.extend_field] if config.extend_field else None  

    event_exp = f"""{unstr_field_en} in {documents}   """ # 关键词要在非结构化字段里 and {unstr_field_en} like "%{key_word}%" ==> 导致 查询企业的话如果企业在，公司就无法被查询到
    search_result = milvus_opt.query_with_filter(
        output_fields=[extend_field_en, unstr_field_en] if extend_field_en else [unstr_field_en],
        filter_exp=event_exp,
        limit=config.limit)
    if extend_field_en:
        ext_dicts = [{config.extend_field: each_data[extend_field_en], unstr_filed:  each_data[unstr_field_en]} 
                    for each_data in search_result] 
    else:
        ext_dicts = [{ unstr_filed:  each_data[unstr_field_en]} for each_data in search_result] 
    # 要让诉求地址在前面，因为内容描述里很多“上述地址” 所以尽量让诉求地址在前面
    # [{"诉求地址": xxx, "内容描述": xxx, }, {}, {}]

    output_ner = await enr_ext_chain.abatch([{"key_word_json": key_word_format, "query": query, 'document_with_address': d} for d in ext_dicts])
    # print(len(output_ner), output_ner)

    outputs = []
    new_documents = []
    for ext_dict, each_output in zip(ext_dicts, output_ner):
        
        if len(each_output) == 0:  # output_output = {}
            continue 
        if [each_output[key_word] for key_word in key_words] == [''] * len(key_words): # value 均为""
            continue 
        if [each_output[key_word] for key_word in key_words] == ['未提及'] * len(key_words): # value 均为"未提及"
            continue 
        
        if extend_field_en:
            ext_dict.pop(config.extend_field)  

        new_documents.append(ext_dict[unstr_filed])

        ext_dict.update(each_output)
        outputs.append(ext_dict)
    # outputs -> [{"地址": 'xx', "内容描述"：xx, "抽取的信息": xx}, {}, {}]

    
    # 按照第一个抽取的信息的数量进行排序
    key_word = key_words[0]
    extracted_entities = list(collapse([d[key_word] for d in outputs if key_word in d])) # collapse 操作是为了让其中某些元素是列表的情况展平为实体，为了解决存在抽取了多个实体的问题
    detail_docs = [d[config.unstructured_column] for d in outputs if key_word in d]
    
    new_output = sorted(Counter(extracted_entities).items(), key=lambda x: x[1], reverse=True)
    new_output = dict(new_output)    
    output_list =  [{key_word: key, '数量': value} for key, value in new_output.items()]
    
    return {'documents': new_documents,  'outputs': {'result': output_list, 'detail': detail_docs}}


async def documents_cluster_summary(state):
    logger.info('开始对非结构化文档进行聚合总结')
    
    documents = state['documents']
    dense_emb = state['outputs']

    if len(documents) == 0:
        return {"outputs": {'result': [], 'detail': []}}
    assert len(documents) == dense_emb.shape[0], '文档数量必定与嵌入模型数目一致'
    documents_cluster = unstr_cluster([doc for doc in documents], dense_emb)  

     # documents_cluster[1: ] 把背景过滤掉
    detail_docs = []
    for cluster in documents_cluster[1: ]:
        detail_docs.extend(cluster[0])


    # 聚类
    summary_list = []
    for sub_docs, count in documents_cluster:
        selected_docs = random.sample(sub_docs, min(20, len(sub_docs)))
        generation = summary_chain.invoke({"docs_list": selected_docs})  # 如果多于20则只拿前面20个作为要总结的事情
        summary_list.append({"主题": generation, "数量": count, }) # related_columns[-1]: sub_docs

    # 分离不需要排序的第一个元素和需要排序的其余部分
    background = summary_list[0]
    # 按照字典中的'数量'值从高到低排序, 第一个是背景（DBSCAN)
    sorted_summary_list = sorted(summary_list[1: ], key=lambda x: x['数量'], reverse=True)

    return {'outputs': {'result': sorted_summary_list, 'detail': detail_docs}}




async def documents_simorder(state):
    logger.info('开始多人同诉聚类')
    filter_exp = state['filter_exp']
    milvus_opt = state['milvus_opt']
    schema = state['schema']
    
    unstructured_field = config.columns_map[config.unstructured_column] 
    address_field = await address_find_chain.ainvoke({"schema": schema})
    address_zh_list = address_field['address_field']
    address_list = [config.columns_map[addr_field] for addr_field in address_zh_list if f'`{addr_field}`' in schema] # 只要保证输出的字段在schema里
    logger.info(f'多人同诉地址字段： {address_list}')
    search_result = milvus_opt.query_with_filter(
        output_fields=address_list + [unstructured_field, 'dense'],  # 除了`内容描述`之外选择使用哪些字段应该由query解析的结果决定
        filter_exp=filter_exp, 
        limit = config.limit)
    logger.info(f'多人同诉检索到的工单总数量为：{len(search_result)}')
    addr_list = ['-'.join([each_result[addr] if each_result[addr] is not None else '' for addr in address_list]) for each_result in search_result]
    docs_list = [retr_result[unstructured_field] for retr_result in search_result]
    if len(docs_list)== 0:
        return  {'outputs': {'result': [], 'detail': []}}
    
    theme_embeddings = np.array([retr_result['dense'] for retr_result in search_result])
    address_embeddings = embedding_bge(addr_list)

    # alpha固定取1，地址和内容权重一样
    cluster_label = search_best_cluster_combine(theme_embeddings, address_embeddings, eps=0.65, alpha_list=[0.6, 1])
    print(cluster_label)
    
    # {label1: order_list1, label2: order_list2, ...}
    grouped_dict = {int(label): [docs_list[i] for i in range(len(cluster_label)) if cluster_label[i] == label]
                    for label in set(cluster_label)}


    label2theme = build_label2theme_with_batch(grouped_dict, simorder_chain)
  
    sentence_list = list(label2theme.values())
    embeddings_sent = embedding_bge(sentence_list) 

    cluster_labels = dbscan_infer(embeddings_sent, 0.6, 2) # -1, -1, 0, 0, -1, -1 ...
    cluster_labels = [label for label in cluster_labels]

    # 根据原始的标签与主题的映射变量label2theme 与 聚类后的标签cluster_labels 生成新的
    new_label2theme = update_mapping(label2theme, cluster_labels)
    logger.info(f'多人同诉输出结果：{new_label2theme}')

    # 创建新的列表，包含每个样本对应的主题、地址和工单
    mapped_texts = [{'theme':new_label2theme[label], 'simorder': addr + '  ' + doc  } for doc, addr, label in zip(docs_list, addr_list, cluster_label) if label != -1]
    detail_docs = [doc for doc, label in zip(docs_list, cluster_label) if label != -1]
    # 1. 按照 'theme' 排序（groupby 要求输入是排序后的数据）
    mapped_texts.sort(key=itemgetter('theme'))
    # 2. 使用 groupby 对 theme 分组，并提取 simorder 到列表中
    result = [
        {key: [item['simorder'] for item in group]}
        for key, group in groupby(mapped_texts, key=itemgetter('theme'))
    ] # [{"theme1": [doc1, doc2, doc3]}, {"theme2": [doc4, doc5]}]


    return  {'outputs': {'result': result, 'detail': detail_docs}}