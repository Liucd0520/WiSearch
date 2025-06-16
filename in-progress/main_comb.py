from initialization.initialize import Config





if __name__ == "__main__":
    config = Config("config/config.toml")

    llm = config.set_llm()
    embedding = config.set_embedding()
    mysql = config.set_mysql()
    milvus = config.set_milvus()



    print(llm.invoke("你好").content)

    query = ['你好', 'hello']
    print(embedding.invoke(query * 100))

    string = ''
    for item in (["REPORT_TEST1", "REPORT_TEST2"]):
        string += mysql.retrieve_meta(item) + '\n'

    prompt = f"""
你是一名MySQL数据库专家。
请根据提供的数据库结构，为用户生成一个用于从数据库查询回答问题所需数据的查询语句。
数据库名:
finData
数据库结构:
{string}

约束:
1. 根据用户的问题，理解用户的意图。使用提供的数据库结构，生成一个语法正确的mysql SQL查询指令。如果回答用户的问题不需要使用SQL查询指令，则直接回答问题即可。
2. 根据各个字段的示例值，判断可能包含所需数据的字段。
3. 如果用户没有特别指定，则使用LIMIT将查询结果最大值限制在50个结果。
4. 只能使用提供的数据库结构中包含的表来生成SQL查询指令。如果根据提供的数据库结构，无法生成SQL，则回答: "无法根据提供的表结构生成SQL。"不允许随意捏造数据。
5. 注意在生成过程中不要错误使用数据表和数据列之间的关系。
6. 确保生成的SQL查询语句是正确可执行的，且运行效率够高。
用户提问:
有哪些项目和人工智能有关
请一步一步思考，并根据以下JSON格式进行回复:
{{
    "thoughts": "thoughts summary to say to user",
    "sql": "SQL Query to run"
}}
确保回复是正确的JSON格式，并可以用Python json.loads进行解析。.
"""
    print(llm.invoke(prompt).content)

    try:
        print(mysql.execute_query("SHOW t2.DEPT, t2.SECONDDEPT, t2.PROJECT_NAME, t2.TRCCB AS 投入产出比 FROM REPORT_TEST2 t2 ORDER BY t2.TRCCB DESC LIMIT 5;"))
    except Exception as e:
        print(f"{e}")
    

    # print(mysql.get_column_items("DEPT", "REPORT_TEST1"))
    """print(mysql.drop_view("TEST"))
    print(mysql.create_view("TEST", "REPORT_TEST2", ["DEPT", "SECONDDEPT"], ["大数据事业部", "企业行业应用业务部"]))
    print(mysql.retrieve_meta("REPORT_TEST2"))
    print(mysql.drop_view("TEST"))"""
