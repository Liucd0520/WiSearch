
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
from module.prompt import *
from utils.util import *
import json 
import copy 
from langchain.schema.runnable import Runnable
from models.langchain_models import llm_qwen_14B
import json 
import os 



def schema_linking(query: str, 
                   schema: str, 
                   related_columns: list = [], 
                   values_dict: dict = {},
                   examples: list = [], 
                   chain: Runnable = None):
    

    import time 
    start_time = time.time()
    output = chain.invoke({"schema": schema, "query": query, "samples": examples})
    print('schema linking cost',  time.time() - start_time)
    
    old_output = copy.deepcopy(output)
    cond_columns = copy.deepcopy(output['condition_columns'])

    print(f"cond_columns: {cond_columns}")

    for condition_field, condition_value in cond_columns.items():
        if condition_field not in related_columns: # 条件字段要与字典库里的匹配
            continue
       
        # 查询字典库，如果字典库里有，则更新
        renew_dict = {}
        for k, v in values_dict.items():  
            if condition_value in v:  
                renew_dict.update({k: condition_value})
        # 如果字典库里有匹配上的，则更新，否则扔给非结构化字段
        if len(renew_dict) > 0: # 意味着有匹配上的
            output['condition_columns'].pop(condition_field) 
            output['condition_columns'].update(renew_dict)
        else:    
            # 意味着四级分类里的值没有与之对应的，当related_columns里最后一个字段不在标签体系里时则扔给非结构化字段
            if related_columns[-1] not in values_dict.keys():  
                unstructured_field = related_columns[-1]
                output['condition_columns'].pop(condition_field)
                output['condition_columns'].update({unstructured_field: condition_value})
            else:
                pass 

    return  output


def sql_gen(query: str, columns: dict, schema: str, chain: Runnable):
    # 利用上一步schema补全的结果    
            
    output = chain.invoke({"schema": schema, "query": query, "columns": columns})
    
    return output['SQL']


# 2025-05-08 23:29:43,535 ChatBI->     INFO     query: 船舶领域的工匠有多少人
# schema linking cost 1.6677849292755127
# cond_columns: {'所属行业': '船舶'}
# 2025-05-08 23:29:45,220 ChatBI->     INFO     schema linking: {'target_columns': ['所属行业'], 'condition_columns': {'区局': '船舶'}}