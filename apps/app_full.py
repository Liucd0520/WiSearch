from pathlib import Path
import sys 
import os 
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)


from models.langchain_models import llm_qwen_7B
from utils.util import *
from langchain.prompts import PromptTemplate

from configs import config as config
from offline_initial_file import init
from langchain_community.utilities import SQLDatabase

from sql_processing.text2sql import schema_linking, sql_gen, sql_gen_without_sl, sql_gen_sl, chat
from sql_processing.choose_sql import choose_sql
from sql_processing.poimask import poi_mask
from sql_processing.timemask import datetime_retriever
from sql_processing.rewrite_check import rewrite
from sql_processing.search import online_search
from sql_processing.sql_assumption import assumption_sql
from sql_processing.view_manager import create_temp_view, sql_replace_view, drop_view

from schema_linking.chain_link import chain_link
from schema_linking.case_retrieval import retrieve_cases

from chathistory.history import ChatHistory, history_preprocess

import uuid
import json

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
    
    rewrite_query = query

    # 语句1生成
    table_list, schema_1 = chain_link(rewrite_query)
    gen_result_1 = sql_gen_without_sl(rewrite_query, schema_1)

    # 语句2生成
    '''case_list, corpus, embedding_corpus = example_preprocess('./examples_PP.json')
    top_indices = retrieve_cases(query, embedding_corpus)
    filtered_list, select_case_list = example_postprocess(case_list, top_indices)
    gen_result_2 = sql_gen_sl(table_list, filtered_list)
    print(gen_result_1)

    # 选择
    choice = choose_sql(query, [gen_result_1, gen_result_2])'''

    return gen_result_1



if __name__ == '__main__':
    '''session_id = str(uuid.uuid4())
    message_id_1 = str(uuid.uuid4())
    message_id_2 = str(uuid.uuid4())'''
    # InitChatHistory.update_history(session_id, message_id_1, 'HUMAN: 2024年的一审判决案件中，有多少案件的嫌疑人是男性')
    # InitChatHistory.update_history(session_id, message_id_2, 'AI: 2024年的一审判决案件中，嫌疑人是男性的案件有15起')
    '''retrieved = InitChatHistory.retrieve_history(session_id)
    print(retrieved)'''
    query = '近1个月虹口区发生了多少起城市管理类的投诉事件'
    print(main(query))