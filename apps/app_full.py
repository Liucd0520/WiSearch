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
    st = time.time()
    assumption = assumption_chain.invoke({"query":query})
    print("ASSUMPTION:", assumption, query)
    ft = time.time()
    print(ft - st)

    # 关键点mask
    st = time.time()
    with open("metadata/table_list_12345.txt", 'r', encoding='utf-8') as f:
        content = f.read()
    poi = poi_mask_chain.invoke({"query": query, "metadata": content})
    # 没办法很好的进行多级分类，需要手动replace
    print("POI:", poi, query)
    ft = time.time()
    print(ft - st)

    # 时间mask
    st = time.time()
    time_mask = time_mask_chain.invoke({"query": query, "date": f"当前时间是{datetime.now().year}年, {datetime.now().month}月，{datetime.now().day}日，{datetime.now().hour}时，{datetime.now().minute}分，{datetime.now().second}秒"})
    print("TIME:", time_mask, query)
    ft = time.time()
    print(ft - st)

    # schema关联
    # linking = schema_linking_chain.invoke({"query": query, "schema": content, "samples": samples})

    

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
    main("近1个月虹口区发生了多少起城市管理类的投诉事件")