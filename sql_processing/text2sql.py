
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
from models.langchain_models import llm_qwen_14B, embedding_bge
import json 
import os 

def schema_linking(query: str, 
                   schema: str, 
                   related_columns: list = [], 
                   values_dict: dict = {},
                   examples: list = [], 
                   chain: Runnable = None):
    start_time = time.time()
    output = chain.invoke({"schema": schema, "query": query, "samples": examples})
    
    old_output = copy.deepcopy(output)
    cond_columns = copy.deepcopy(output['condition_columns'])

    print(f"cond_columns: {cond_columns}")

    for condition_field, condition_value in cond_columns.items():
        if condition_field not in related_columns: # 条件字段要与字典库里的匹配
            continue
       
        renew_dict = {}
        for k, v in values_dict.items():  
            if condition_value in v:  
                renew_dict.update({k: condition_value})
        
        if len(renew_dict) > 0: # 意味着有匹配上的
            output['condition_columns'].pop(condition_field) 
            output['condition_columns'].update(renew_dict)
        else:   
            unstructured_field = config.unstructrued_column
            # 意味着四级分类里的值没有与之对应的，那就扔给非结构化字段
            output['condition_columns'].pop(condition_field)
            output['condition_columns'].update({unstructured_field: condition_value})

    return  old_output, output

def schema_linking_nochain(query, schema, related_columns, values_dict, examples):
    prompt = PromptTemplate(template=schema_link_prompt, input_variables=['schema', 'samples', 'query'])
    chain = create_json_chain(llm_qwen_14B, prompt)

    output = chain.invoke({"schema":schema, "samples": examples, "query":query})
    old_output = copy.deepcopy(output)
    cond_columns = copy.deepcopy(output['条件列'])
    for condition_field, condition_value in cond_columns.items():
        if condition_field not in related_columns: # 条件字段要与字典库里的匹配
            continue
        
        renew_dict = {}
        for k, v in values_dict.items():  # k: 一级分类,v: [xx, xx]
            if condition_value in v:  # 判断条件的值是不是在字典的某一层级对应的值里
                renew_dict.update({k: condition_value})
        
        if len(renew_dict) > 0: # 意味着有匹配上的
            output['条件列'].pop(condition_field) 
            output['条件列'].update(renew_dict)
        else:   
            unstructured_field = config.unstructrued_column
            # 意味着四级分类里的值没有与之对应的，那就扔给非结构化字段
            output['条件列'].pop(condition_field)
            output['条件列'].update({unstructured_field: condition_value})
        target_list = output['目标列']
        for item in target_list:
            if item not in schema:
                target_list.remove(item)
        output['目标列'] = target_list

    return old_output, output

def sql_gen(query: str, columns: dict, schema: str, chain: Runnable):
    # 利用上一步schema补全的结果    
            
    output = chain.invoke({"schema": schema, "query": query, "columns": columns})
    
    return output

def sql_gen_sl(schema_list, filtered_list):
    schema_string = ';'.join(schema_list)
    multi_schema_dict = ''
    for i in range(len(schema_list)):
        table_name = schema_list[i]
        with open(f'related_values_{table_name}.json', 'r', encoding='utf-8') as f_json:
            values_dict = json.load(f_json)
        related_field = list(values_dict.keys())
        db, table = table_name.split('.', 1)
        with open(f'meta_data_{db}_{table}.txt', 'r', encoding='utf-8') as f:
            schema = f.read()
        pattern = re.compile(r'`(\w+)` 类型: (\w+); 含义: (.*?(?=;))')
        matches = pattern.findall(schema)
        pattern_string = ''
        for match in matches:
            column_name, column_type, column_descrip = match
            pattern_string = pattern_string + f'-{column_name} {column_type} {column_descrip}\n'
        _, columns_dict = schema_linking_nochain(query, schema, related_field, values_dict, examples='\n'.join(filtered_list))
        multi_schema_dict += f'### 表名：{table_name}\n### 表结构\n{pattern_string}\n### 查询数据列：{json.dumps(columns_dict, ensure_ascii=False)}\n'

    prompt = PromptTemplate(template=sql_gen_sl_prompt, input_variables=['query','table','input'])
    chain = create_json_chain(llm_qwen_14B, prompt)
    output = chain.invoke({"query":query,"table":schema_string,"input":multi_schema_dict})
    sql = output['SQL']
    return sql

def sql_gen_without_sl(query: str, columns: list):
    prompt = PromptTemplate(template=sql_gen_without_sl_prompt, input_variables=['query','tables','columns'])
    chain = create_json_chain(llm_qwen_14B, prompt)
    tables = []
    for i in range(len(columns)):
        table, para = columns[i].split('.',1 )
        tables.append('table')
    gen_result = chain.invoke({"query":query, "tables": ';'.join(tables), "columns":';'.join(columns)})

    # print(gen_result['SQL'])
    return gen_result['SQL']

def chat(query: str, sql_result: str):
    prompt = PromptTemplate(template=chat_prompt, input_variables=['query','sql_result'])
    chain = create_str_chain(llm_qwen_14B, prompt)

    chat_response = chain.invoke({"query":query, "sql_result":sql_result})

    return chat_response

if __name__ == "__main__":
    query = '有多少项目的主要负责人是Dane，给我这些项目的编号'
    columns = ['PROJECT_INFO.MEM(成员名称: 记录项目成员的名称, 示例值: Dane)', 'PROJECT_INFO.PN(项目名称: 记录项目的唯一名称, 示例值: ZERO,INITIAL)']
    sql_result = '案件总数 \n 15'

    # chat_response = chat(query, sql_result)
    sql_gen_response = sql_gen_without_sl(query, columns)
    print(sql_gen_response)