import pymilvus
from typing import Optional

class MILVUS:
    def __init__(self, **kwargs):
        self.client = pymilvus.MilvusClient(
            **kwargs
        )
        self.type_mapping ={
            "text": pymilvus.DataType.VARCHAR,
            "longtext": pymilvus.DataType.VARCHAR,
            "bigint": pymilvus.DataType.INT64,
            "tinyint": pymilvus.DataType.INT32,
            "smallint": pymilvus.DataType.INT32,
            "mediumint": pymilvus.DataType.INT32,
            'float': pymilvus.DataType.FLOAT,
            'double': pymilvus.DataType.DOUBLE,
            'decimal': pymilvus.DataType.DOUBLE,
            'boolean': pymilvus.DataType.BOOL,
            'enum': pymilvus.DataType.VARCHAR,
            'set': pymilvus.DataType.VARCHAR,
            'datetime': pymilvus.DataType.VARCHAR,
            'char': pymilvus.DataType.VARCHAR,
            'varchar': pymilvus.DataType.VARCHAR,
            'json': pymilvus.DataType.JSON,
        }

    def add_collection(self, name, primary, dim, field_name, datatype, max_length, auto_id: Optional[bool]=False, enable_dynamic_field: Optional[bool]=True):
        schema = self.client.create_schema(
            auto_id = auto_id,
            enable_dynamic_field = enable_dynamic_field
        )
        for i in range(len(field_name)):
            if field_name == primary:
                schema.add_field(field_name=field_name, datatype=self.type_mapping[datatype[i]], is_primary=True, max_length=max_length[i])
            else:
                schema.add_field(field_name=field_name, datatype=self.type_mapping[datatype[i]], max_length=max_length[i])
        schema.add_field(field_name="sparse", datatype=pymilvus.DataType.SPARSE_FLOAT_VECTOR)
        schema.add_field(field_name="dense", datatype=pymilvus.DataType.FLOAT_VECTOR, dim=dim)

        # Prepare index parameters
        index_params = self.client.prepare_index_params()

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


        client.create_collection(
            collection_name=name,
            schema=schema,
            index_params=index_params
        )

if __name__ == "__main__":
    client = MILVUS(uri='http://172.31.24.111:19530')
    print(client.list_databases())