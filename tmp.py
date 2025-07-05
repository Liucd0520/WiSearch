import simplejson

a = "SELECT `PROJECT_NAME`, `PROJECT_TYPE`, `DEPT`, `START_TIME`, `END_TIME`, `SRS`, `CBS`, `CCB` FROM AI_ASK_TEST_202506181425 WHERE `PROJECT_NAME` LIKE '%市民热线项目%' LIMIT 5000;"
b = simplejson.dumps({"sql_gen": a}, ensure_ascii=False)
print(b)
