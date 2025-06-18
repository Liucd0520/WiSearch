import os
import sys

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

# from tools.metadata_gen import sql_create, update

from chathistory.history import ChatHistory, history_preprocess

import uuid
import json
import pymysql

from apps.app_full import main

from openpyxl import load_workbook


class Dataset:
    def __init__(self, path='/data/liyiru/WiSearch/eval/Query.xlsx'):
        wb = load_workbook(path)
        sheet = wb['结构化查询']

        self.query = []
        for row in sheet.iter_rows(min_row=2, min_col=1, max_col=1, max_row=sheet.max_row, values_only=True):
            if row[0] is not None:
                self.query.append(row[0])

        self.result = []
        for row in sheet.iter_rows(min_row=2, min_col=2, max_col=2, max_row=sheet.max_row, values_only=True):
            if row[0] is not None:
                self.result.append(row[0])

        self.sql = []
        for row in sheet.iter_rows(min_row=2, min_col=3, max_col=3, max_row=sheet.max_row, values_only=True):
            if row[0] is not None:
                self.sql.append(row[0])

def eval(dataset, pipeline, conn):

    cursor = conn.cursor()
    
    sql_list = []
    result_list = []

    for item in dataset.query:
        sql = pipeline(item)
        sql_list.append(sql)
        result = cursor.execute(sql)
        result_list.append(result)

    accuracy = ''
    sql_list = []
    result_list = []




    return {"accuracy": accuracy, "sql": sql_list, "result": result_list}




if __name__ == "__main__":
    dataset = Dataset()
    # print(dataset.query)
    # print(dataset.result)
    # print(dataset.sql)

    db_conn = pymysql.connect(
    host='172.31.24.111',
    user='root',
    password='liucd123',
    database='12345',
    port=3307,
    charset='utf8mb4',
    )

    cursor = db_conn.cursor()

    cursor.execute('SHOW CREATE TABLE shanghai')

    eval(dataset, main, db_conn)

    # print(cursor.fetchall()[0])


