from langchain_openai import ChatOpenAI
from openai import OpenAI
import numpy as np 

class LLM:
    def __init__(self, **kwargs):
        self.client = ChatOpenAI(
            **kwargs
        )

    def invoke(self, text):
        return self.client.invoke(text)

class EMBEDDING:
    def __init__(self, api_key, base_url, model_name):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def invoke(self, text):
        responses = self.client.embeddings.create(input=text, model=self.model_name)
        embedding_list = [output_data.embedding for output_data in responses.data]

        return np.array(embedding_list)[0]