import pymysql

class MYSQL:
    def __init__(self, **kwargs):
        self.connector = pymysql.connect(
            **kwargs
        )

    def execute_query(self, query):
        with self.connector.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def get_column_items(self, column_name, table_name):
        query = f"SELECT DISTINCT {column_name} FROM {table_name}"
        return self.execute_query(query)
        
    def retrieve_meta(self, table_name):
        query = f"SHOW CREATE TABLE {table_name};"
        with self.connector.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()[0][1]
        
    def create_view(self, view_name, table_name, paras, values):
        if not values:
            return table_name
        else:
            if len(values) == 1:
                query = f"""
CREATE VIEW {view_name} AS
SELECT * FROM {table_name}
WHERE {paras[0]} = '{values[0]}'
"""
                print(query)

            else:
                query_list = []
                for i in range(len(paras)):
                    query_list.append(f"{paras[i]} = '{values[i]}'")
                query_str = ' AND '.join(query_list)
                query = f"""
CREATE VIEW {view_name} AS
SELECT * FROM {table_name}
WHERE {query_str}
"""
                print(query)
                
            with self.connector.cursor() as cursor:
                cursor.execute(query)
            return view_name
        
    def drop_view(self, view_name):
        query = f"DROP VIEW IF EXISTS {view_name}"
        with self.connector.cursor() as cursor:
            cursor.execute(query)