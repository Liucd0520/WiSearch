from pathlib import Path
import sys 
import os 
import json
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

def samples_gen(query_list: list, schema: str, chain: Runnable) -> list:
    
    if query_list is None:
        return []
    
    example_list = []
    for query in query_list:
        print(f"query: {query}")
        columns_dict = chain.invoke({"schema": schema, "query": query, "samples": ''})
        print(f"columns_dict: {columns_dict}")


        example = {'query': query}
        example.update(columns_dict)  # example: {query: xxx, 目标列: xxx, '条件列': xxx}
        example_list.append(example, )

    return example_list

if __name__ == '__main__':
    schema_path = 'data/gwdata_meta_data.txt'
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = f.read()
    query_list = ['查询2024年1月1日到2024年1月31日，朝阳街道的工单数量', 
                  '查询近1年陆家嘴街道的派出所的工单分布',
                  '查询川沙片区关于诈骗事件随月份的变化趋势']

    mysql_uri = 'mysql+mysqlconnector://root:liucd123@localhost:3306/pdga'
    table_name = 'gwdata'
    file_path = os.path.join('data', f'{table_name}_schema_linking_samples.json')
    # schema linking samples generation
    prompt_samples_gen = PromptTemplate(template=schema_link_prompt, input_variables=["schema", "query", 'samples'])
    linking_chain = create_json_chain(llm_qwen_14B, prompt_samples_gen)
    result = samples_gen(query_list, schema, linking_chain)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)


