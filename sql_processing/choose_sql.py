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

def choose_sql(query, candidates):
    """
    从不同方式生成的SQL中选择最合适的SQL指令

    参数：
        query (str): 输入的问题
        candidates (list): 生成的SQL
    
    返回：
        result (str): 最终选择的SQL
    
    """
    prompt = PromptTemplate(template=choice_prompt, variables=["query", "candi"])
    chain = create_json_chain(model=llm_qwen_7B, prompt=prompt)
    candi = ''
    for i in range(len(candidates)):
        item = candidates[i]
        candi += f"选项{i+1} {item}\n"
        print("candi:", candi)
    output = chain.invoke({"query":query, "candi":candi})
    _, result = output['explain'], output['sql']
    print(_)

    return result

if __name__ == '__main__':
    query = '2024年宜兴市院的办案数量'
    candidates = ['SELECT COUNT(BMSAH) AS 办案数量 FROM aj_yx_aj WHERE YEAR(ZHXGSJ) = 2024 AND CBDW_MC = "宜兴市院"', 'SELECT DISTINCT BMSAH AS 办案数量 FROM aj_yx_aj WHERE YEAR(ZHXGSJ) = 2024 AND CBDW_MC = "宜兴市院"']
    result = choose_sql(query, candidates)
    print("RESULT:", result)