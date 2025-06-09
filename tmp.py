from pymilvus import MilvusClient
from configs import config
client = MilvusClient(uri=config.uri)
ret = client.query(collection_name=config.collection_name, filter='gd_contact_sex_cn == "未知" ',limit=16383 )
print(ret)
