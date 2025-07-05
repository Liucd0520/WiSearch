from fastapi import WebSocket
from typing import List
from utils.util import * 

clients: List[WebSocket] = []

# 发送消息给所有连接的客户端
async def send_to_clients(message: str):
    if len(message) < 20:
        logger.info(f'websocket发送的数据为：{message}')

    for client in clients:
        await client.send_text(message)


if __name__  == '__main__':
    import json 
    import asyncio
    obtain_data = [{'所属居委': '祥东居委'}, {'所属居委': '前进居委'}, {'所属居委': '纪念居委'}, {'所属居委': '和平居委'}, {'所属居委': '庆阳居委'}, {'所属居委': '镇西居委'}, {'所属居委': '横滨居委'}, {'所属居委': '东四居委'}, {'所属居委': '凉六居委'}, {'所属居委': '虹湾居委'}]
    result = asyncio.run(send_to_clients(json.dumps({"response": obtain_data}, ensure_ascii=False)))
    print(result)