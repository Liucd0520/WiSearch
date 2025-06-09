
from langchain_community.utilities import SQLDatabase


def create_temp_view(mysql_db, table_name: str, view_index: str, values):
    # 如果values为空，则不创建视图
    if not values:
        return 
    
    view_table_name = f"{table_name}_{values}"
    view_sql = f"""
    CREATE VIEW {view_table_name} AS
    SELECT * FROM {table_name}
    WHERE `{view_index}` = '{values}'

    """
    
    mysql_db.run(view_sql)

    return view_table_name

def drop_view(mysql_db, table_names: list):

    for table_name in table_names:
        drop_view_sql = f"DROP VIEW IF EXISTS {table_name}"
        mysql_db.run(drop_view_sql)
    return 

def sql_replace_view(original_sql: str, table_name: str, view_table_name: str):
    # 将原表换成View
    return original_sql.replace(table_name, view_table_name)

if __name__ == "__main__":
    mysql_uri = 'mysql+pymysql://root:liucd123@localhost:3306/huangpu'
    table_name = 'huangpu_fayuan'
    view_index = '使用部门' 
    view_values = '法警大队'
    original_sql = f"select * from {table_name} "
    view_table_name = create_temp_view(mysql_uri, table_name, view_index, view_values)
    print(view_table_name)
    view_sql = sql_replace_view(original_sql, table_name, view_table_name)
    print(view_sql)
    

# 存在schema-linking文件夹以及  函数名为schema linking的情况
