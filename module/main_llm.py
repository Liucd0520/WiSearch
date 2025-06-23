
from pathlib import Path
import sys 
import os 
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)


from langchain.prompts import PromptTemplate
from module.structured_output import create_json_chain, create_structured_chain, create_str_chain
from module.prompt import *
from pydantic import BaseModel, Field
from typing import List, Literal
from datetime import datetime

# 任务感知模型
def task_aware_model(model):
    prompt = PromptTemplate(template=task_aware_prompt, input_variables=["query", ])
    task_chain = create_json_chain(prompt, model, )

    return task_chain



def schema_linking_model(model):  
    prompt_schema_linking = PromptTemplate(template=schema_link_prompt, input_variables=["schema", "query", 'samples'])
    linking_chain = create_json_chain(prompt_schema_linking, model )

    return linking_chain


def sql_gen_model(model):
    prompt_sql_gen = PromptTemplate(template=sql_gen_prompt, input_variables=["schema", "query", 'columns'])
    sql_gen_chain = create_json_chain(prompt_sql_gen, model)

    return sql_gen_chain


# 

# 命名实体判别模型
class GradeDocuments(BaseModel):

    binary_score: Literal["yes", "no"] = Field(
        ...,
        description="Documents are relevant to the question, 'yes' or 'no'",
    )
    # reason: str

def ner_clf_model(model):
    prompt = PromptTemplate(template=ner_prompt, input_variables=["input", ])
    ner_clf_chain = create_structured_chain(prompt, model, GradeDocuments)
    
    return ner_clf_chain




# SQL 重写模型
class SQLGen(BaseModel):
    """generation sql statement."""
    sql: str = Field(
            description="sql statement"
        )
    
def sql_feedback_model(model):
    prompt = PromptTemplate(template=sql_feedback_prompt, input_variables=["schema", "old_sql", "error"])
    sql_rewrite_chain = create_structured_chain( prompt, model, SQLGen)

    return sql_rewrite_chain


def meta_data_model(model):
    prompt_meta_data = PromptTemplate(template=metadata_prompt, input_variables=["schema", "enum_values", 'samples' ])
    meta_data_chain = create_str_chain(prompt_meta_data, model)

    return meta_data_chain

def each_meta_data_model(model):
    # meta data 
    """生成某个字段的元数据，field_info与enum_values均为某个字段"""
    prompt_meta_data = PromptTemplate(template=each_metadata_prompt, input_variables=["db_info", "full_schema", "field_info",  "enum_values", ])
    each_meta_data_chain = create_str_chain(prompt_meta_data, model)
    
    return each_meta_data_chain

def translate_english_model(model):
    prompt = PromptTemplate(template=translate_prompt, input_variables=["word", ])
    translate_chain = create_str_chain(prompt, model)

    return translate_chain

class DateTimeModel(BaseModel):
    create_time: List[datetime]

def datetime_interval_model(model):
    prompt = PromptTemplate(template=datetime_prompt, input_variables=["query, now"])
    datetime_interval_chain =  create_structured_chain( prompt, model, structured_data=DateTimeModel)

    return datetime_interval_chain

# 额外工具

def choose_sql_model(model):
    prompt = PromptTemplate(template=choice_prompt, variables=["query", "candi"])
    chain = create_json_chain(model=model, prompt=prompt)

    return chain

def error_rewrite_model(model):
    prompt = PromptTemplate(template=error_rewrite_prompt, input_variables=['query','columns','schema','generated_sql','error_message'])
    chain = create_json_chain(model=model, prompt=prompt)

    return chain

def check_query_model(model):
    prompt = PromptTemplate(template=check_query_prompt, input_variables=['query','generated_sql','retrieved_result'])
    chain = create_json_chain(model=model, prompt=prompt)

    return chain

def poi_mask_model(model):
    prompt = PromptTemplate(template=mask_prompt, variables=["query", "metadata", "values"])
    chain = create_json_chain(model=model, prompt=prompt)

    return chain

def rewrite_check_model(model):
    prompt = PromptTemplate(template=check_prompt, variables=['query', 'history'])
    chain = create_json_chain(model=model, prompt=prompt)

    return chain

def rewrite_model(model):
    prompt = PromptTemplate(template=write_prompt, variables=['query', 'history'])
    chain = create_json_chain(model=model, prompt=prompt)

    return chain

def abstract_model(model):
    prompt = PromptTemplate(template=abstract_prompt, variables=["query", "content"])
    chain = create_str_chain(model=model, prompt=prompt)

    return chain

def assumption_model(model):
    prompt = PromptTemplate(template=assumption_prompt, variables=['query'])
    chain = create_json_chain(model=model, prompt=prompt)

    return chain

def time_mask_model(model):
    prompt = PromptTemplate(template=time_mask_prompt, variables=["query"])
    chain = create_json_chain(model=model, prompt=prompt)
    
    return chain

def time_process_model(model):
    prompt = PromptTemplate(template=time_process_prompt, variables=["query"])
    chain = create_json_chain(model=model, prompt=prompt)

    return chain

def sql_gen_sl_model(model):
    prompt = PromptTemplate(template=sql_gen_sl_prompt, variables=["query", "table", "time"])
    chain = create_json_chain(model=model, prompt=prompt)

    return chain

def sql_gen_mask_model(model):
    prompt = PromptTemplate(template=sql_gen_mask_prompt, variables=["query", "table", "time"])
    chain = create_json_chain(model=model, prompt=prompt)

    return chain

def choose_para_model(model):
    prompt = PromptTemplate(template=choose_para_prompt, variables=["query", "values", "key"])
    chain = create_json_chain(model=model, prompt=prompt)

    return chain

