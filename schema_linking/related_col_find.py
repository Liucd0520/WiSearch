from pathlib import Path
import sys 
import os 
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)


from typing import List, Dict
from langchain_community.utilities import SQLDatabase
from utils.util import *
import json 
import os 



def get_distinct_values(
    mysql_uri: str,
    table_name: str,
    columns: List[str],
    max_distinct_values: int = 1000
) -> Dict[str, List[str]]:
    """
    获取指定字段的所有不同值并保存为字典

    Args:
        mysql_uri: MySQL数据库连接URI
        table_name: 表名
        columns: 需要查找不同值的字段列表
        save_path: 结果保存路径
        batch_size: 每次查询的批次大小
        max_distinct_values: 每个字段最大允许的不同值数量

    Returns:
        Dict[str, List[str]]: 字段名到其不同值列表的映射
    """
    try:
        # 创建数据库连接
        mysql_db = SQLDatabase.from_uri(mysql_uri)
        distinct_values = {}

        # 验证字段是否存在
        columns_query = f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table_name}'
            AND TABLE_SCHEMA = DATABASE()
        """
        valid_columns = [col[0] for col in eval(mysql_db.run(columns_query))]
        
        # 过滤出有效的字段
        valid_columns_to_process = [
            col for col in columns 
            if col in valid_columns
        ]

        if not valid_columns_to_process:
            logger.error(f"No valid columns found in {columns}")
            return {}

        values = {}
        # 对每个字段获取不同值
        for column in valid_columns_to_process[:-1]:
            try:
                logger.info(f"Processing column: {column}")
                
                # 首先获取不同值的数量
                count_query = f"""
                    SELECT DISTINCT {column}
                    FROM {table_name}
                    WHERE {column} IS NOT NULL
                """
                distinct_values = mysql_db.run(count_query)
                distinct_values = [item[0] for item in eval(distinct_values)]
                print(f"distinct_values: {distinct_values}")

                if len(distinct_values) > max_distinct_values:
                    logger.warning(
                        f"Column {column} has {distinct_values} distinct values, "
                        f"exceeding limit of {max_distinct_values}. Skipping."
                    )
                else:
                    values[column] = distinct_values

                    logger.info(f"Found {len(distinct_values)} distinct values for {column}")

            except Exception as e:
                logger.error(f"Error processing column {column}: {str(e)}")
                continue

        return values

    except Exception as e:
        logger.error(f"Error in get_distinct_values: {str(e)}")
        return {}

if __name__ == "__main__":
    


    save_dir = 'data'

    # 获取指定字段的不同值
    distinct_values = get_distinct_values(
        mysql_uri = 'mysql+mysqlconnector://root:liucd123@localhost:3306/pdga',    
        table_name = 'gwdata',
        columns= [] #['BJAY1', 'BJAY2', ],
    )
    print(distinct_values)

    # # 保存结果到文件
    # save_path = os.path.join(save_dir, 'distinct_values.json')
    # with open(save_path, 'w', encoding='utf-8') as f:
    #     json.dump(distinct_values, f, ensure_ascii=False, indent=2)
    # logger.info(f"Results saved to {save_path}")


