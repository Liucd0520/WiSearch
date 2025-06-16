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

def rewrite(query, history):
    rewrite_check_prompt = PromptTemplate(template=check_prompt, variables=['query', 'history'])
    rewrite_check_chain = create_json_chain(llm_qwen_14B, rewrite_check_prompt)
    rewrite_prompt = PromptTemplate(template=write_prompt, variables=['query', 'history'])
    rewrite_chain = create_json_chain(llm_qwen_14B, rewrite_prompt)

    rewrite_check_output = rewrite_check_chain.invoke({"query":query,"history":history})
    rewrite_check = rewrite_check_output['necessity']
    print(rewrite_check)
    if rewrite_check == '需要':
        rewrite_query_output = rewrite_chain.invoke({"query":query,"history":history})
        rewrite_query = rewrite_query_output['rewrite_query']
    else:
        rewrite_query = query

    return rewrite_query, rewrite_check

if __name__ == '__main__':
    query = '男性呢'
    history = '上一轮对话:去年处理的一审判决案件中，有多少案件嫌疑人是女性?'
    rewrited_query = rewrite(query, history)
    print(rewrited_query)