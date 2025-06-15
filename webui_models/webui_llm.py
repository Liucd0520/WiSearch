

from langchain.prompts import PromptTemplate
from module.structured_output import create_json_chain, create_structured_chain, create_str_chain
from webui_models.prompt import *
# 任务感知模型
def query_insight_model(model):

    prompt = PromptTemplate(template=query_explanation_prompt, input_variables=["schema", "query", "columns_dict"])
    explanation_chain =  create_str_chain(prompt, model)

    return explanation_chain


def result_chat_model(model):
    prompt_chat =  PromptTemplate(template=chat_prompt, input_variables=['query',  "obtain_data" ])
    llm_chat_chain = create_str_chain(prompt_chat, model)  # 这里是以coder_14的模型

    return llm_chat_chain


def query_recommand_model(model):
    prompt_recommand = PromptTemplate(template=recommand_prompt, input_variables=['query', "schema", "obtain_data" ])
    llm_recommand_chain = create_json_chain(prompt_recommand, model)  # 这里是以coder_14的模型
    
    return llm_recommand_chain


