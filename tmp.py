from langchain_community.utilities import SQLDatabase
 

# def get_distinct_values(
#     mysql_db,
#     table_name: str,
#     column_list: list, 
#     LIMIT: int = 100000):
#     """
#     获取表中制定列名的枚举值
#     """
#     result = {}
#     for column_name in column_list:
#         distinct_query = f"""
#             SELECT DISTINCT `{column_name}`
#             FROM `{table_name}` 
#             WHERE `{column_name}` IS NOT NULL 
#             LIMIT {LIMIT}
#         """

#         distinct_values = mysql_db.run(distinct_query, include_columns=True)
#         distinct_values = eval(distinct_values)
#         dist_dict =  {column_name: [d[column_name] for d in distinct_values]}
#         result.update(dist_dict)
    
#     # result: {'事项名称': [x, x, x], 'xx': [x, x, x,]}
#     return result




import concurrent.futures

def get_distinct_values(
    mysql_db,
    table_name: str,
    column_list: list, 
    LIMIT: int = 100000,
    max_workers: int = 5):
    """使用多线程并行执行多个单列查询"""
    
    def fetch_column_distinct(column_name):
        distinct_query = f"""
            SELECT DISTINCT `{column_name}`
            FROM `{table_name}` 
            WHERE `{column_name}` IS NOT NULL 
            LIMIT {LIMIT}
        """
        try:
            distinct_values = mysql_db.run(distinct_query, include_columns=True)
            distinct_values = eval(distinct_values)
            return {column_name: [d[column_name] for d in distinct_values]}
        except Exception as e:
            print(f"Error fetching {column_name}: {e}")
            return {column_name: []}
    
    # 使用线程池并行执行查询
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_col = {executor.submit(fetch_column_distinct, col): col for col in column_list}
        
        result = {}
        for future in concurrent.futures.as_completed(future_to_col):
            col = future_to_col[future]
            try:
                col_result = future.result()
                result.update(col_result)
            except Exception as e:
                print(f"Error processing {col}: {e}")
    
    return result


if __name__ == '__main__':
    mysql_uri = 'mysql+mysqlconnector://root:liucd123@172.31.24.111:3307/12345_half'
    mysql_db = SQLDatabase.from_uri(mysql_uri)

    import time 
    start = time.time()

    result = get_distinct_values(mysql_db, table_name='tmp2', column_list=['一级分类', '二级分类', '三级分类', '四级分类', '新一级分类', '新二级分类', '新三级分类', '新四级分类'])
    print(result)
    print(time.time() - start)

