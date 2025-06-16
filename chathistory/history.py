from pathlib import Path
import sys
import os

import time
from collections import OrderedDict
import uuid
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

import redis
import json

'''def redis_config(host='localhost', port=6379, password=None, db="11"):
    redis_client = redis.StrictRedis(host=host, port=port, db=db, password=password)
    return redis_client

redis_client = redis_config(host='172.31.24.110',port=33062, password='uRcqOhkjO6@32Tv1')'''

class ChatHistory:
    def __init__(self):
        self.history: dict = OrderedDict()

    def update_history(self, session_id, message_id, chat_message):
        chat_time = time.time()
        if session_id in self.history:
            self.history[session_id][message_id] = chat_message
        else:
            self.history[session_id] = OrderedDict()
            self.history[session_id][message_id] = chat_message

    def retrieve_history(self, session_id, message_id=None):
        if message_id:
            try:
                retrieved = self.history[session_id][message_id]
            except:
                retrieved = 'AI: '
        else:
            try:
                retrieved = self.history[session_id]
            except:
                retrieved = OrderedDict()
        return retrieved

    def clear_history(self, session_id):
        if session_id in self.history:
            del self.history[session_id]

class ChatHistoryRedis:
    def __init__(self, host='localhost', port=6379, password=None, db='11'):
        self.redis_client = redis.StrictRedis(host=host, port=port, db=db, password=password)

    def update_history(self, session_id, message_id, chat_message):
        chat_time = time.time()
        data = {"message":chat_message}
        self.redis_client.set(f"history:{session_id}:{message_id}",json.dumps(data, ensure_ascii=False))

    def retrieve_history(self, session_id, message_id=None):
        if message_id:
            try:
                retrieved = json.loads(self.redis_client.get(f"history:{session_id}:{message_id}"))['message']
            except:
                retrieved = 'AI: '
        else:
            try:
                keys = self.redis_client.keys(f"history:{session_id}:*")
                retrieved = OrderedDict()
                for key in keys:
                    key = key.decode('utf-8')
                    message_key = key.split(':')[-1]
                    retrieved[f'{message_key}'] = json.loads(self.redis_client.get(key).decode('utf-8'))['message']
            except:
                retrieved = OrderedDict()
        return retrieved

    def clear_history(self, session_id):
        keys = self.redis_client.keys(f"history:{session_id}:*")
        for key in keys:
            self.redis_client.delete(key)


def history_preprocess(history):
    history_len = int(len(history) / 2)

    oldest_history = ''
    older_history = ''
    # old_history = '上一轮对话:\n'
    history_content = list(history.values())
    if history_len >= 4:
        oldest_history += '更早对话:\n'
        for j in range(history_len-3,0,-1):
            oldest_history = oldest_history + f'{history_content[-(j*2)+7]}\n{history_content[-(j*2)+8]}\n'
    if history_len >= 2:
        older_history += '最近对话:\n'
        for j in range(history_len-1,0,-1):
            older_history = older_history + f'{history_content[-(j*2)+3]}\n{history_content[-(j*2)+4]}\n'
    old_history = f'上一轮对话:\n{history_content[-1]}\n{history_content[-2]}'
    history_string  = f'{oldest_history}{older_history}{old_history}'

    return history_string


if __name__ == "__main__":
    history = ChatHistoryRedis(host='172.31.24.110',port=33062, password='uRcqOhkjO6@32Tv1')
    # history = ChatHistory()
    session_id = str(uuid.uuid4())
    message_id_1 = str(uuid.uuid4())
    message_id_2 = str(uuid.uuid4())
    history.update_history(session_id, message_id_1, "HUMAN: HELLO!")
    history.update_history(session_id, message_id_2, "AI: HELLO THERE!")
    print(history.retrieve_history(session_id))
    print(history.retrieve_history(session_id, message_id_1))
    history.clear_history(session_id)
    print(history.retrieve_history(session_id))