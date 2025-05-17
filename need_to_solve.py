from models.langchain_models import llm_qwen_14B
from fastapi import FastAPI, WebSocket
import uvicorn
from utils.util import *
import time 
from langchain_openai import  ChatOpenAI
from openai import OpenAI
import numpy as np 


app = FastAPI()



llm_qwen_14B = ChatOpenAI(model="text2sql2",  
                    base_url='http://192.168.0.11:8012/v1', 
                    # base_url='http://192.168.0.11:33071/v1', 
                    api_key='EMPTY',
                    temperature=0,
                    )


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        message = await websocket.receive_text()
        print(f"{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))}:  Received message: {message}")
     
        await websocket.send_text('开始')
        async for chunk in llm_qwen_14B.astream("你好。告诉我一些关于你自己的事情"):
            
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())),   chunk.content)
            await websocket.send_text(chunk.content)

if __name__ == '__main__':
    
    uvicorn.run(app=app, host='0.0.0.0', port=33064)


