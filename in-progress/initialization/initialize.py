import numpy as np 
import json
from models.model import LLM, EMBEDDING
from database.mysql import MYSQL
from knowledge.milvus import MILVUS

import pymilvus

from langchain_community.document_loaders import TomlLoader

from typing import Optional, List, Dict

class Config():
    def __init__(self, path: Optional[str] = "../config/config.toml"):
        try:
            loader = TomlLoader(path)
            self.rule = json.loads(loader.load()[0].page_content)
        except Exception as e:
            print(f"{e}")
        
    def set_llm(self):
        return LLM(
            **self.rule["LLM"]
        )
    
    def set_embedding(self):
        return EMBEDDING(
            **self.rule["EMBEDDING"]
        )

    def set_mysql(self):
        return MYSQL(
            **self.rule["MYSQL"]
        )

    def set_milvus(self):
        return MILVUS(
            **self.rule["MILVUS"]
        )
