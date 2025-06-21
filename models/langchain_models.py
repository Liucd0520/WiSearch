
from langchain_openai import  ChatOpenAI
from openai import OpenAI
import numpy as np 

llm_qwen_14B = ChatOpenAI(model="text2sql2",  
                    # base_url='http://192.168.0.11:8012/v1', 
                    # base_url='http://172.31.24.23:8003/v1',
                    base_url='http://172.31.24.111:33071/v1',  
                    api_key='EMPTY',
                    temperature=0,
                    )

'''llm_qwen_7B = ChatOpenAI(model="Qwen2.5-7B-Instruct",  
                    # base_url='http://192.168.0.11:8011/v1', 
                    base_url='http://172.31.24.111:9050/v1', 
                    api_key='EMPTY',
                    temperature=0,
                    )'''

llm_qwen_7B = ChatOpenAI(model="Qwen2.5-7B-Instruct",  
                    # base_url='http://192.168.0.11:8011/v1', 
                    base_url='http://172.31.24.111:9050/v1', 
                    api_key='EMPTY',
                    temperature=0,
                    )

openai_api_key_emb = "EMPTY"
openai_api_base_emb = 'http://172.31.24.111:8003/v1' # 'http://10.218.1.3:8049/v1'  #  'http://172.31.24.23:8002/v1' # 'http://192.168.0.11:8076/v1' 

client_emb = OpenAI(api_key=openai_api_key_emb,
                base_url=openai_api_base_emb
                )

def embedding_bge(query_list):
    
    responses = client_emb.embeddings.create(
        input=query_list,
        model='bge-large-embedding',
    )
    embedding_list = [output_data.embedding for output_data in  responses.data]
    
    return np.array(embedding_list)


# embedding_bge(['你好'])

# print('---')
# result = llm_qwen_14B.invoke('你好') 
# print(result)
result = llm_qwen_7B.invoke('你好') 
print(result)


if __name__ == '__main__':
    query = ['你好', 'hello']
    result = embedding_bge(query * 100)
    print(result[0])

    result2 = embedding_bge(query[:1])
    print(result2.shape)
