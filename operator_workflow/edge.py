from pydantic import BaseModel, Field
from typing import Literal
from operator_workflow.prompt import query_router_prompt_template, create_judge_extend_prompt
from langchain.prompts import PromptTemplate
from operator_workflow.utils import create_structured_chain

# Data model
class RouteQuery(BaseModel):
    """Route a user query to the most relevant intent."""

    intent: Literal["NER", "ThemeSummary"] = Field(
        ...,
        description="Given a user question choose to route it to low level extraction(NER) or a high level abstraction(ThemeSummary).",
    )


def query_router(state):

    print('开始进行查询路由...')

    query = state["query"]
    prompt = PromptTemplate(template=query_router_prompt_template, input_variables=["query", ])

    rounter_chain = create_structured_chain(prompt, RouteQuery)
    generation = rounter_chain.invoke({"query": query})
    intent = generation.intent
    print('选择节点：', intent)
    
    return intent # NER or Summary


class GradeExtraction(BaseModel):
    """评估信息抽取结果是否正确."""

    binary_score: Literal["yes", "no"] = Field(
        ...,
        description="Evaluate whether the information extraction results are correct. yes for correct and no for incorrect",
    )
    reason: str = Field(..., description="give the grade reason")


def is_extension(state):
    # 目前没有用扩展
    """according to query and extracted information to judge whether extend action excuted or not """

    query = state['query']
    output_content = state['outputs']
    
    print('-----进入扩展与否的条件判断--')
    print(output_content)

    prompt = PromptTemplate(template=create_judge_extend_prompt, input_variables=["query", 'extracted_info'])
    extend_chain = create_structured_chain(prompt, GradeExtraction)
    generation = extend_chain.invoke({'query': query, 'extracted_info': output_content})

    score = generation.binary_score

    return score

