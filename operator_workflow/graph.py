from typing_extensions import TypedDict
from typing import Literal, List


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        query: query
        db_name: database name
        documents: list of documents
    """

    query: str
    unstr_value: str
    filter_exp: str 
    milvus_opt: object 
    documents: List[str]    
    outputs: List[str]

