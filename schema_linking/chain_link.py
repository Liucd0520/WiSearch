from pathlib import Path
import sys 
import os 
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from prompts.prompt import *
from models.langchain_models import llm_qwen_14B
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable
from utils.util import *

def chain_link(query, databases=None, tables=None):
    """
    根据输入问题，由大模型从库→表→字段进行阶段式的关键字段选择。

    参数：
        query (str): 输入的问题。
        databases Optional(list): 手动选择的数据库 ['chatbiNew','chatbi']
        tables Optional(list): 手动选择的数据表 ['chatbiNew.aj_yx_aj', 'chatbi.t_tyyw_xj_xlj_aj']

    返回：
        list of str: 大模型选择的对sql生成有用的字段 ['chatbiNew.aj_yx_aj.BMSAH', 'chatbi.t_tyyw_xj_xlj_aj.AJMC']
    
    """
    
    db_prompt = PromptTemplate(template=metadata_db_prompt, input_variables=["schema","question"])
    db_chain = create_json_chain(llm_qwen_14B, db_prompt)
    table_prompt = PromptTemplate(template=metadata_table_prompt, input_variables=["schema","question"])
    table_chain = create_json_chain(llm_qwen_14B, table_prompt)
    para_prompt = PromptTemplate(template=metadata_para_prompt, input_variables=["schema","question"])
    para_chain = create_json_chain(llm_qwen_14B, para_prompt)

    # 数据库筛选
    if databases:
        dbs = databases
    else:
        with open('./database_list.txt', 'r', encoding='utf-8') as f_db_list:
            db_list = '\n'.join(f_db_list)
        meta_db = db_chain.invoke({"schema":db_list,"question":query})
        print("META DB:", meta_db)
        explanations, dbs = meta_db['explanations'], meta_db['databases']

    # 数据表筛选
    table_list_total = []
    if tables:
        table_list_total = tables
    else:
        for selected_db in dbs:
            print("SELECTED DB:", selected_db)
            with open(f'./{selected_db}_list.txt', 'r', encoding='utf-8') as f_table_list:
                table_list = '\n'.join(f_table_list)
            meta_table = table_chain.invoke({"schema":table_list,"question":query})
            print("META TABLE:", meta_table)
            explanations, tables = meta_table['explanations'], list(map(lambda x: f'{selected_db}.' + x, meta_table['tables']))
            table_list_total += tables
    
    # 字段筛选
    para_list_total = []
    for selected_table in table_list_total:
        db_name, table_name = selected_table.split('.', 1)
        with open(f'./meta_data_{db_name}_{table_name}.txt', 'r', encoding='utf-8') as f_para_list:
            para_list = '\n'.join(f_para_list)
        meta_para = para_chain.invoke({"schema":para_list,"question":query})
        print("META PARA:", meta_para)
        explanations, paras = meta_para['explanations'], meta_para['paras']
        para_list_total += paras

    return table_list_total, para_list_total

if __name__ == "__main__":
    # 示例

    query = "有多少项目的主要负责人是Dane，给我这些项目的编号"
    para_list = chain_link(query)

    print(para_list)