import redis
import json
import uuid
from collections import OrderedDict


def redis_config(host='localhost', port=6379, password=None, db="12"):
    redis_client = redis.StrictRedis(host=host, port=port, db=db, password=password)
    return redis_client

redis_client = redis_config(host='172.31.24.110',port=33062, password='uRcqOhkjO6@32Tv1')

session_id = str(uuid.uuid4())
message_id_1 = str(uuid.uuid4())
message_id_2 = str(uuid.uuid4())

data_1 = {"message":"HUMAN: HELLO!"}
data_2 = {"message":"AI: HELLO THERE!"}
redis_client.set(f"history:{session_id}:{message_id_1}",json.dumps(data_1, ensure_ascii=False))
redis_client.set(f"history:{session_id}:{message_id_2}",json.dumps(data_2, ensure_ascii=False))

retrieved = redis_client.get(f"history:{session_id}:{message_id_1}")
# print(json.loads(retrieved)['message'])


retrieved_all = redis_client.keys(f"history:{session_id}:*")
data = OrderedDict()
for key in retrieved_all:
    key = key.decode('utf-8')
    message_key = key.split(':')[-1]
    data[f'{message_key}'] = json.loads(redis_client.get(key).decode('utf-8'))['message']
print(data)

