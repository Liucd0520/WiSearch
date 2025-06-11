
from pathlib import Path
import sys 
import os 
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain_community.utilities import SQLDatabase
from langchain.prompts import PromptTemplate
from prompts.prompt import *
from models.langchain_models import llm_qwen_14B
from utils.util import *
from langchain.schema.runnable import Runnable
from typing import Dict, List


def get_enum_values(
    mysql_uri: str,
    table_name: str,
    max_distinct_values: int = 50,
    max_combined_length: int = 300,
    LIMIT : int = 1000
) -> Dict[str, List[str]]:
    """
    获取表中所有可能的枚举字段及其值

    Args:
        mysql_uri: MySQL数据库连接URI
        table_name: 表名
        max_distinct_values: 最大不同值数量，超过此数量不视为枚举
        max_combined_length: 所有值组合的最大长度，超过此长度不视为枚举

    Returns:
        Dict[str, List[str]]: 字段名到其枚举值列表的映射
        例如: {'status': ['active', 'inactive', 'pending']}
    """
    try:
        # 创建数据库连接
        mysql_db = SQLDatabase.from_uri(mysql_uri)
        
        # 获取表的所有列名
        columns_query = f"""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{table_name}'
            AND TABLE_SCHEMA = DATABASE()
        """
        columns_result = mysql_db.run(columns_query)
        columns_result = eval(columns_result)
        print(f"columns_result: {columns_result}")
        enum_values = {}
        
        # 对每个列进行分析
        for column_info in columns_result:  
            column_name = column_info[0]
            data_type = column_info[1]
            print(f"column_name: {column_name}, data_type: {data_type}")

            # 跳过不适合作为枚举的数据类型
            if data_type.lower() not in ['enum', 'char', 'varchar', 
                                         'text', 'longtext', 
                                         'bool', 'boolean',
                                        'tinyint', 'int', 'bigint', # 状态码
                                         ]:
                continue
            
            # 获取distinct值
            distinct_query = f"""
                SELECT DISTINCT {column_name} 
                FROM {table_name} 
                WHERE {column_name} IS NOT NULL 
                LIMIT {LIMIT}
            """
            
            try:
                distinct_values = mysql_db.run(distinct_query)
                distinct_values = eval(distinct_values) # [('202306131337523532389448',), ]
                distinct_values = [v[0] for v in distinct_values]
                print(f"distinct_sample_values: {distinct_values[:10]}")

                # 检查是否符合枚举条件
                if len(distinct_values) <= max_distinct_values:
                    # 计算所有值组合的总长度
                    combined_length = sum(len(str(v)) for v in distinct_values)
                    if combined_length <= max_combined_length:
                        enum_values[column_name] = sorted(distinct_values)
                        logger.info(f"Found enum field: {column_name} with {len(distinct_values)} values")
                
            except Exception as e:
                logger.warning(f"Error processing column {column_name}: {str(e)}")
                continue
        
        return enum_values
        
    except Exception as e:
        logger.error(f"Error in get_enum_values: {str(e)}")
        return {}


def meta_data_gen(mysql_uri: str, table_name: str,  chain: Runnable, is_supplement: bool = True) -> bool:
        
    mysql_db = SQLDatabase.from_uri(mysql_uri, sample_rows_in_table_info=3)
    schema_with_samples = mysql_db.get_table_info(table_names=[table_name],)  
    
    # 如果is_supplement为False，则不进行补全
    if not is_supplement:

        return schema_with_samples, True
        

    # 对schema里的元数据描述进行补全，方便模型定位到正确的列
    schema, samples = split_metadata(schema_with_samples)
    enum_values = get_enum_values(mysql_uri, table_name)
    logger.info(f"enum_values: {enum_values}")
    
    new_schema = chain.invoke({'schema': schema, 'enum_values': enum_values, 'samples': samples})            
    new_schema_with_samples = merge_metadata(new_schema, samples)

    # 便于检查是否有误
    more_than, less_than = check_schema(new_schema=new_schema, old_schema=schema)

    if more_than == [] and less_than == []:
        return new_schema_with_samples, True 
    else:
        return new_schema_with_samples, False


if __name__ == '__main__':
    mysql_uri = 'mysql+mysqlconnector://root:liucd123@localhost:3306/pdga'    
    table_name = 'gwdata'
    file_path = os.path.join('data', f'{table_name}_meta_data.txt')
    # meta data 
    prompt_meta_data = PromptTemplate(template=metadata_prompt, input_variables=["schema", "enum_values", 'samples' ])
    meta_data_chain = create_str_chain(llm_qwen_14B, prompt_meta_data)
    schema_gen, is_True = meta_data_gen(mysql_uri, table_name, meta_data_chain, is_supplement=True)
    
    if is_True:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(schema_gen, )
    else:
        print(f"meta data gen failed, please check the schema and samples")
