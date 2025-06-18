
from pathlib import Path
import sys 
import os 
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)


import pymysql
# from langchain import OpenAI, SQLDatabase, SQLDatabaseChain
from langchain_community.utilities import SQLDatabase
from langchain.prompts import PromptTemplate
import time 
from langchain_openai import  ChatOpenAI
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from prompts.prompt import *
from utils.util import *
import json 
import copy 
from langchain.schema.runnable import Runnable
from models.langchain_models import llm_qwen_7B, embedding_bge
import json 
import os 
from module.structured_output import *

def error_rewrite(query: str, columns: dict, schema: str, generated_sql: str, error_message: str):
    prompt = PromptTemplate(template=error_rewrite_prompt, input_variables=['query','columns','schema','generated_sql','error_message'])
    chain = create_json_chain(model=llm_qwen_7B, prompt=prompt)

    output = chain.invoke({{"schema": schema, "query": query, "columns": columns, "generated_sql": generated_sql, "error_message": error_message}})

    return output

def check_query(query: str, generated_sql: str, retrieved_result):
    prompt = PromptTemplate(template=check_query_prompt, input_variables=['query','generated_sql','retrieved_result'])
    chain = create_json_chain(model=llm_qwen_7B, prompt=prompt)

    output = chain.invoke({"query": query, "generated_sql": generated_sql, "retrieved_result": retrieved_result})

    return output