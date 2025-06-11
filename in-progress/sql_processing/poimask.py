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
from models.langchain_models import llm_qwen_14B, llm_qwen_7B
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable
from utils.util import *

def poi_mask(query, sql):
    """"""

    prompt = PromptTemplate(template=mask_prompt, variables=["query", "SQL"])
    chain = create_json_chain(llm_qwen_14B, prompt)
    output = chain.invoke({"query":query, "SQL":sql})
    masked_query = output['masked_query']

    return masked_query

if __name__ == '__main__':
    query = '2024年宜兴市院一审判决的案件中，有多少嫌疑人是男性的案件被撤销了'
    sql = "SELECT COUNT(*) FROM cases WHERE YEAR(judgment_date) = 2024 AND court = '宜兴市院' AND judgment_level = '一审' AND case_status LIKE '%撤销%' AND suspect_gender LIKE '%男%'"
    masked_query = poi_mask(query, sql)
    print("MASKED QUERY:", masked_query)