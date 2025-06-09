from sqlalchemy import create_engine
import mysql.connector
from mysql.connector import Error
from sqlalchemy import create_engine, text

def execute_sql_file(file_path, connection_string):
    engine = create_engine(connection_string)
    
    try:
        with open(file_path, 'r') as file:
            sql_commands = file.read().split(';')
        
        with engine.connect() as connection:
            for command in sql_commands:
                stripped_command = command.strip()
                if stripped_command:  # 确保不是空命令
                    # 使用text()包裹SQL字符串
                    print(stripped_command)
                    connection.execute(text(stripped_command))
        print("SQL文件执行成功")
    except Exception as e:
        print(f"执行SQL文件时出错：{e}")


# 示例调用
execute_sql_file('shanghai.sql', 'mysql+mysqlconnector://root:liucd123@172.31.24.111:3307/12345')