from pymilvus import MilvusClient
from models.langchain_models import embedding_bge
from pymilvus import MilvusClient, DataType
from configs import config
from datetime import datetime

type_mapping ={
    "text": DataType.VARCHAR,
    "longtext": DataType.VARCHAR,
    "bigint": DataType.INT64,
    "tinyint": DataType.INT32,
    "smallint": DataType.INT32,
    "mediumint": DataType.INT32,
    'float': DataType.FLOAT,
    'double': DataType.DOUBLE,
    'decimal': DataType.DOUBLE,
    'boolean': DataType.BOOL,
    'enum': DataType.VARCHAR,
    'set': DataType.VARCHAR,
    'datetime': DataType.VARCHAR,
    'char': DataType.VARCHAR,
    'varchar': DataType.VARCHAR,
    'json': DataType.JSON,
}



def build_index(client):

    # Prepare index parameters
    index_params = client.prepare_index_params()

    # Add indexes
    index_params.add_index(
        field_name="dense",
        index_name="dense_index",
        index_type="IVF_FLAT",
        metric_type="IP",
        params={"nlist": 128},
    )

    index_params.add_index(
        field_name="sparse",
        index_name="sparse_index",
        index_type="SPARSE_INVERTED_INDEX",  # Index type for sparse vectors
        metric_type="IP",  # Currently, only IP (Inner Product) is supported for sparse vectors
        params={"drop_ratio_build": 0.2},  # The ratio of small vector values to be dropped during indexing
    )

    return index_params





def mysql_field_operator(mysql_db, table_name):
    """获取 MySQL 表中的字段名和类型"""

    cmd = f'SHOW FIELDS FROM {table_name};'
    print(cmd)
    result = eval(mysql_db.run(cmd))

    field_list, type_list = [], []
    for item in result:
        print(item)
        mysql_field, mysql_type = item[0], item[1]
        field_list.append(mysql_field)
        type_list.append(mysql_type)
    
    return field_list, type_list

def build_schema(mysql_db, mysql_table_name, primary_key_name, columns_map):
    # Create schema
    schema = MilvusClient.create_schema(
        auto_id=False,
        enable_dynamic_field=True,
    )

    field_list, type_list = mysql_field_operator(mysql_db, mysql_table_name)
    
    for field_name_mysql, field_type in zip(field_list, type_list):
        print(field_name_mysql, field_type)

        field_name = columns_map[field_name_mysql]
        milvus_type = type_mapping[field_type]
        print('==>', milvus_type)

        # 检查是否需要设置 max_length 参数
        extra_params = {}
        if milvus_type == DataType.VARCHAR:  # 根据实际情况替换 'VARCHAR'
            extra_params['max_length'] = 65535  # 设置你想要的最大长度

        if field_name == columns_map[primary_key_name]:
            schema.add_field(field_name=field_name, datatype=milvus_type, **extra_params, is_primary=True)
            continue 
        schema.add_field(field_name=field_name, datatype=milvus_type, nullable=True, **extra_params, ) # max_length=10000,

    schema.add_field(field_name="sparse", datatype=DataType.SPARSE_FLOAT_VECTOR)
    schema.add_field(field_name="dense", datatype=DataType.FLOAT_VECTOR, dim=embedding_bge(['你好']).shape[-1])   # dim: 

    return schema


