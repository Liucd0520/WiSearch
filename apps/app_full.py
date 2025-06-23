from pathlib import Path
import sys 
import os 
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)


from models.langchain_models import llm_qwen_7B, embedding_bge
from utils.util import *

from langchain.prompts import PromptTemplate

from configs import config as config
from offline_initial_file import init
from langchain_community.utilities import SQLDatabase

from models.create_chain import *

from sql_processing.text2sql import schema_linking
from schema_linking.chain_link import chain_link
from schema_linking.case_retrieval import retrieve_cases

from chathistory.history import ChatHistory, history_preprocess

import uuid
import json
import time
from datetime import datetime

InitChatHistory = ChatHistory()

# query = 'Dane的项目有哪些'

def main(query):
    '''if session_id == '':
        session_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())'''
    # history = InitChatHistory.retrieve_history(session_id)
    '''if history != []:
        history_string = history_preprocess(history)
        print("HISTORY:", history_string)
        rewrite_query, status = rewrite(query, history_string)
        if status != '需要':
            InitChatHistory.clear_history(session_id)
    else:
        rewrite_query = query

    InitChatHistory.update_history(session_id, message_id, f'Human: {rewrite_query}')'''
    
    # 假设性SQL
    # st = time.time()
    # assumption = assumption_chain.invoke({"query":query})
    # print("ASSUMPTION:", assumption, query)
    # ft = time.time()

    # print(ft - st)

    # 关键点mask
    st_main = time.time()

    st = time.time()
    with open("metadata/table_list_12345.txt", 'r', encoding='utf-8') as f:
        content = f.read()
    with open('metadata/related_values_shanghai_ad_time.json', 'r', encoding='utf-8') as f:
            related_values = json.loads(f.read())
    poi = poi_mask_chain.invoke({"query": query, "metadata": content, "values": related_values})
    # 没办法很好的进行多级分类，需要手动replace
    '''replace_list = ['一级分类', '二级分类', '三级分类', '四级分类', '新一级分类', '新二级分类', '新三级分类', '新四级分类', '新五级分类']
    masked_query = poi['masked_query']
    for replace_element in replace_list:
        masked_query = masked_query.replace(replace_element, "多级分类")'''
    print("POI:", poi, query)
    ft = time.time()
    poi_time = ft - st
    print(ft - st)

    # 时间mask
    st = time.time()
    time_mask = time_mask_chain.invoke({"query": query})
    print("TIME:", time_mask, query)
    time_mask_query = time_mask['masked_query']
    ft = time.time()
    time_mask_time = ft - st
    print(ft - st)

    # 时间处理
    st = time.time()
    time_process = time_process_chain.invoke({"query": time_mask['time_mask']})
    print("TIME P:", time_process, query)
    time_p = time_process['time']
    ft = time.time()
    print(ft - st)
    time_process_time = ft - st

    # schema link
    st = time.time()
    try:
        link_result = f"工单生成时间: {time_p}"
    except:
        link_result = ''

    '''with open(f'metadata/related_values_shanghai_ad_time.json', 'r', encoding='utf-8') as f_json:
        values_dict = json.load(f_json)
    related_field = list(values_dict.keys())

    samples = ''
    for i in range(len(poi['masks'])):
         samples += f'{poi['masks'][i]}: {poi['mask_map'][i]}'

    _, columns_dict = schema_linking(query=time_mask_query, 
                   schema=content, 
                   related_columns=related_field, 
                   values_dict=values_dict,
                   examples=samples, 
                   chain=schema_linking_chain)
    
    print("SCHEMA LINKING:", _, columns_dict)

    link_result += f"查询数据列: {json.dumps(columns_dict, ensure_ascii=False)}"'''


    # linking = schema_linking_chain.invoke({"query": query, "schema": content, "samples": samples})
    for i in range(len(poi['mask_map'])):
        mask = poi['mask_map'][i]
        key = poi['masks'][i]
        with open('./metadata/related_values_shanghai_ad_time.json', 'r', encoding='utf-8') as f:
            related_values = json.loads(f.read())
        
        linking = retrieve_cases_full(query=mask, related_values=related_values, key=key)
        print("SL:", linking, mask, key)
        if linking[0] != '不属于任何字段' or linking[0] != '时间字段' or linking[0] != '询问字段':
            link_result += f' {linking[0]}: {linking[1]}'
        elif linking[0] == '不属于任何字段':
            link_result += f' 内容描述: {linking[1]}'
    ft = time.time()
    print(ft - st)
    schema_link_time = ft - st

    # 生成
    st = time.time()
    generate = sql_gen_mask_chain.invoke({"query": query, "table": content, "time": link_result})
    print(generate)
    ft = time.time()
    generate_time = ft - st

    ft_main = time.time()
    total_time = ft_main - st_main

    return generate['SQL'], {'total': total_time, 'poi_time': poi_time, 'time_mask_time': time_mask_time, 'time_process_time': time_process_time, 'schema_link_time': schema_link_time, 'generate_time': generate_time}

    

    # schema关联
    # linking = schema_linking_chain.invoke({"query": query, "schema": content, "samples": samples})

    # generate = sql_gen_mask_chain.invoke({"query": time_mask_query, "table": content, "time": time_result})

    # print("GENERATE:", generate, query)
    

    # 选择
    

    # return gen_result_1



if __name__ == '__main__':
    '''session_id = str(uuid.uuid4())
    message_id_1 = str(uuid.uuid4())
    message_id_2 = str(uuid.uuid4())'''
    # InitChatHistory.update_history(session_id, message_id_1, 'HUMAN: 2024年的一审判决案件中，有多少案件的嫌疑人是男性')
    # InitChatHistory.update_history(session_id, message_id_2, 'AI: 2024年的一审判决案件中，嫌疑人是男性的案件有15起')
    '''retrieved = InitChatHistory.retrieve_history(session_id)
    print(retrieved)'''
    # query = '近1个月虹口区发生了多少起城市管理类的投诉事件'
    # main("今年上半年企业服务工单里工单类型分别有那些，占比如何")
    main("近1个月虹口区发生了多少起城市管理类的投诉事件")