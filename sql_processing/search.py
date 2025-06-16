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
from models.langchain_models import llm_qwen_14B
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable
from utils.util import *

from langchain_tavily import TavilySearch
os.environ["TAVILY_API_KEY"] = "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"

def online_search(query, search_tool):
    """
    对问题进行联网查询
    
    参数：
        query (str): 输入的问题
        search_tool: 搜索工具生成链
        
    返回：
        output (str): 经过总结后的查询结果
        """
    search_result = search_tool.invoke({"query":query})['results']
    output_result = ''
    for i in range(len(search_result)):
        item = search_result[i]
        output_result += f'\n查询结果{i+1} 标题:{item['title']} 内容:{item['content']}\n'

    print("SEARCH RESULT:", output_result)
    prompt = PromptTemplate(template=abstract_prompt, variables=["query", "content"])
    chain = create_str_chain(llm_qwen_14B, prompt)
    output = chain.invoke({"query":query,"content":output_result})
    return output

if __name__ == '__main__':
    query = '2023年端午节假期的时间范围'
    search_tool = TavilySearch(max_result=3, topic='general')
    output = online_search(query, search_tool)
    print("OUTPUT:", output)