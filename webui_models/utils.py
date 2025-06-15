import asyncio
import re 
from langchain.schema.runnable import Runnable
from utils.util import sql_semantic_rewrite, sql_execute

# 流式生成器函数
async def query_insight_generator(chain, query: str, schema: str, columns_dict: dict, ):
    async for chunk in chain.astream({ 
        "query": query, "schema": schema, "columns_dict": columns_dict
        }):
        yield chunk  # 逐个 token 输出
        await asyncio.sleep(0.01)  # 可选：控制流速


def obtain_detail_data(task_type: str, mysql_uri: str, sql_command: str, schema: str, params: dict, sql_feedback_chain: Runnable ):
    if task_type in ['SQL', '内容分类']:
        pattern = r"(?i)(SELECT\s+)(.*?)(\s+FROM)"
        modified_sql = re.sub(pattern, lambda match: f"{match.group(1)}*{match.group(3)}", sql_command, flags=re.IGNORECASE)
        execute_result = sql_execute(mysql_uri, modified_sql, schema, params, sql_feedback_chain)
        result_detail = eval(execute_result) if  execute_result != '' else [{}]
    else: 
        result_detail = [{}] 

    return result_detail