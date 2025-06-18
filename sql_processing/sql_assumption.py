from pathlib import Path
import sys 
import os 
from datetime import datetime
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from prompts.prompt import *
from models.langchain_models import llm_qwen_7B
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable
from utils.util import *
from module.structured_output import *

def assumption_sql(query):
    """
    对用户提问生成一个可能的SQL查询语句

    参数：
        query (str): 输入的问题

    返回：
        result (str): 生成的SQL查询语句
    """
    prompt = PromptTemplate(template=assumption_prompt, variables=['query'])
    chain = create_json_chain(model=llm_qwen_7B, prompt=prompt)
    output = chain.invoke({"query":query})
    _, result = output['explain'], output['sql']
    print("EXPLAIN:", _)
    return result

if __name__ == '__main__':
    query = '2024年宜兴市院一审判决的案件中，有多少嫌疑人是男性的案件被撤销了'
    output = assumption_sql(query)
    print("OUTPUT:", output)