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
# from models.model import LLM
from langchain.prompts import PromptTemplate
# from langchain.schema.runnable import Runnable
from utils.util import *

from initialization.initialize import Config

from langchain_tavily import TavilySearch
os.environ["TAVILY_API_KEY"] = "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"



def datetime_retriever(query, search_tool):
    """
    对问题中提到的时间进行特殊处理

    参数：
        query (str): 输入的问题
        search_tool: 搜索工具生成链

    返回：
        masked_query: 日期掩码后的问题
        time_mask: 日期掩码
        final_result: 查询结果
    """
    prompt = PromptTemplate(template=time_mask_prompt, variables=["query"])
    chain = create_json_chain(llm_qwen_14B, prompt)
    output = chain.invoke({"query":query, "date":f"当前是{datetime.now().year}年, {datetime.now().month}月，{datetime.now().day}日"})
    masked_query, time_mask = output['masked_query'], output['time_mask']

    search_result = search_tool.invoke({"query":f"{time_mask}的确切日期"})['results']
    output_result = ''
    for i in range(len(search_result)):
        item = search_result[i]
        output_result += f'\n查询结果{i+1} 标题:{item['title']} 内容:{item['content']}\n'
    final_result = llm_qwen_14B.invoke(f'{time_mask}的确切时间范围, {output_result}')

    return masked_query, time_mask, final_result




if __name__ == '__main__':
    query = '前年端午节假期上海站的客流量是多少'
    search_tool = TavilySearch(max_result=3, topic='general')
    masked_query, time_mask, final_result = datetime_retriever(query, search_tool)
    print("MASKED QUERY:", masked_query)
    print("TIME MASK:", time_mask)
    print("FINAL RESULT:", final_result)