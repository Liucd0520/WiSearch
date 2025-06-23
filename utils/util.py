from pathlib import Path
import sys 
import os 
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain.schema.runnable import Runnable
import logging 
import time 
from configs import config as config
import re 
import sqlparse
from langchain.schema.runnable import Runnable
from langchain_community.utilities import SQLDatabase
from configs import config as config
# from datetime import datetime
from configs import config
import random 
import time 
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random
import datetime 
from models.langchain_models import embedding_bge
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json
from models.create_chain import *


def create_path(_path):
    if not os.path.exists(_path):
        os.mkdir(_path)

def get_log(log_dir):

    create_path(log_dir)

    # 1. 记录器
    logger = logging.getLogger('ChatBI-> ')  # 默认以Root作为logger的名字，这里填写liver
    logger.setLevel(logging.DEBUG)        # 将logger级别设为INFO

    #2. 处理器 handler
    consoleHandler = logging.StreamHandler()

    log_name = 'log_{}.log'.format(time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()))
    print(log_name)

    log_path = os.path.join(log_dir, log_name)
    fileHandler = logging.FileHandler(filename=log_path, mode='a', encoding='utf-8') # mode='w' 会覆盖掉重写的内容，'a' 是追加

    # 3. Formatter 格式
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

    # 4. 给处理器设置格式
    consoleHandler.setFormatter(formatter)
    fileHandler.setFormatter(formatter)

    # 5. 记录器设置处理器
    logger.addHandler(consoleHandler)
    logger.addHandler(fileHandler)

    return logger

log_dir = config.log_dir
logger = get_log(log_dir)



def retrieve_cases(query, embedding_corpus, top_k=3):
    """
    根据输入问题从词库中检索最相似的TOP3词条。

    参数:
        query (str): 输入的问题。
        corpus (list of str): 词库，包含多个词条。
        embedding_func (function): 嵌入模型函数，用于将文本转化为向量。

    返回:
        list of tuple: TOP3相似词条及其相似度分数。
    """
    # 将输入问题转化为向量

    query_embedding = embedding_bge(query).reshape(1, -1)  # 确保是二维数组

    # 计算余弦相似度
    similarities = cosine_similarity(query_embedding, embedding_corpus).flatten()
    # 获取相似度最高的TOP3索引
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    # 返回TOP3词条及其相似度分数

    return top_indices

def retrieve_cases_full(query, related_values, key, top_k=3):
    """
    根据输入问题从词库中检索最相似的TOP3词条。

    参数:
        query (str): 输入的问题。
        corpus (dict): 词库，包含多个词条。
        embedding_func (function): 嵌入模型函数，用于将文本转化为向量。

    返回:
        list of tuple: TOP3相似词条及其相似度分数。
    """
    # 将输入问题转化为向量

    sim_key = ''
    similarity = 0
    sim_item = ''
    query_embedding = embedding_bge(query).reshape(1, -1)
    for key, value in related_values.items():
        corpus_embedding = embedding_bge(value)

        similarities = cosine_similarity(query_embedding, corpus_embedding).flatten()
        max_sim = np.max(similarities)
        max_sim_index = np.argmax(similarities)
        # print(max_sim, max_sim_index)
        
        if max_sim > 0.85:
            if max_sim >= similarity:
                print("MATCHED:", max_sim, key, value[max_sim_index])
                similarity = max_sim
                sim_key = key
                sim_item = value[max_sim_index]

    '''if sim_key == '':
        corpus_embedding_advice = embedding_bge(related_values[key])
        similarities_advice = cosine_similarity(query_embedding, corpus_embedding_advice).flatten()
        max_sim = np.max(similarities_advice)
        max_sim_index = np.argmax(similarities_advice)
        # print(max_sim, max_sim_index)
        if max_sim > 0.7:
            if max_sim >= similarity:
                similarity = max_sim
                sim_key = key
                sim_item = value[max_sim_index]'''
    # print(sim_key, sim_item)
        
    

    if sim_key == '':
        sim_result = choose_para_chain.invoke({"query": query, "values": str(related_values), "key": key})
        sim_key = sim_result['decision']
        '''if sim_key != '时间字段' and sim_key != '不属于任何字段':
            value = related_values[f'{sim_key}']
            corpus_embedding = embedding_bge(value)

            similarities = cosine_similarity(query_embedding, corpus_embedding).flatten()
            max_sim = np.max(similarities)
            max_sim_index = np.argmax(similarities)
            sim_item = value[max_sim_index]'''

        sim_item = sim_result['value']
        # print(key, top_indices)

    # print(sim_key, sim_item)

    return sim_key, sim_item


def split_metadata(mysql_schema_with_samples):
    pattern = r'/\*.*?\*/'
    samples = re.findall(pattern, mysql_schema_with_samples, re.DOTALL)[0]
    schema = mysql_schema_with_samples.replace(samples, '')

    return schema, samples


def merge_metadata(schema, samples):
    
    return '\n'.join([schema, samples])

def check_schema(new_schema, old_schema):
    new_field = re.findall(r'`([^`]+)`', new_schema)
    old_field = re.findall(r'`([^`]+)`', old_schema)

    more_than =  list(set(new_field) - set(old_field))
    less_than = list(set(old_field) - set(new_field))

    return more_than, less_than





def unstructured_clause(sql_query, special_column):
    # 使用 sqlparse 解析 SQL 查询
    parsed = sqlparse.parse(sql_query)

    # 提取 WHERE 子句的条件
    where_clause = None
    for statement in parsed:
        if statement.get_type() == 'SELECT' or statement.get_type() == 'select':
            # 找到查询中的 WHERE 子句
            tokens = [token for token in statement.tokens if token.ttype is None]
            for token in tokens:
                if 'WHERE' in token.value or 'where' in token.value:
                    where_clause = token.value.strip()

    # 如果找到了 WHERE 子句
    if where_clause:
        # print("WHERE 子句：", where_clause)
        where_clause = where_clause.replace('WHERE', '').replace('where', '')

        # 查找所有包含 `内容描述` 字段的条件
        conditions = []
        # 处理连接符 AND 和 OR
        # 将 AND 和 OR 替换为统一的符号，便于后续分割
        where_clause = where_clause.replace(' and ', ' AND ').replace('or', ' OR ')

        # 分割 WHERE 子句为独立的条件
        tokens = where_clause.split('AND')
        all_conditions = []
        for token in tokens:
            or_conditions = token.split('OR')
            for condition in or_conditions:
                all_conditions.append(condition.strip())

        # 查找包含 `内容描述` 字段的条件
        for condition in all_conditions:
            if special_column in condition: # special_column = related_columns[-1]
                conditions.append(condition.strip().replace('(', '').replace(')', ''))
        
        return conditions
    else:
        return []
    



def unstructure_value_extract(sql_query, unstructured_column):
    conditions = unstructured_clause(sql_query, unstructured_column)

    value_dict = {}
    for condintion in conditions:
        if 'LIKE' in condintion or 'like' in condintion:
            pattern = r'like\s*([\'"])(.*?)\1'
            match = re.search(pattern, condintion, re.IGNORECASE)  # re.IGNORECASE 不缺乏大小写
            value = match.group(2)
            value = value.replace('%', '')  # 去掉like 后面的%
                
        elif '=' in condintion:
            pattern = r'=\s*([\'"])(.*?)\1' 
            match = re.search(pattern, condintion)
            
            value = match.group(2)
        
        value_dict.update({condintion: value})  
    
    return value_dict

def abbr_value_extract(sql_query, abbr_column):
    return unstructure_value_extract(sql_query, abbr_column)


import sqlparse
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML

def remove_group_by(sql):
    # 解析SQL语句
    parsed = sqlparse.parse(sql)
    stmt = parsed[0]  # 假定只有一个SQL语句
    
    new_tokens = []
    group_by_seen = False
    having_seen = False
    
    for token in stmt.tokens:
        if token.ttype is Keyword and token.value.upper() == 'GROUP BY':
            group_by_seen = True
            continue  # 跳过GROUP BY及其后续直到HAVING之前的token
        
        if group_by_seen and isinstance(token, IdentifierList):
            # 跳过IdentifierList内的内容，假设这是GROUP BY后的列名列表
            continue
        
        if group_by_seen and token.ttype is Keyword and token.value.upper() == 'HAVING':
            having_seen = True
            continue  # 跳过HAVING及其后续的内容
        
        if not group_by_seen or (group_by_seen and having_seen and token.ttype is None and not isinstance(token, Identifier)):
            new_tokens.append(token)
        
        if having_seen and token.ttype is None and not isinstance(token, Identifier):
            # 当我们遇到非标识符且非None类型的token时，停止忽略token
            group_by_seen = False
            having_seen = False
        
        if token.ttype is DML and token.value.upper() == 'SELECT':
            # 处理聚合函数 - 这里简化处理，实际中需要更复杂的逻辑来识别并处理聚合函数
            pass  # 需要额外逻辑来处理聚合函数，这取决于具体情况

    # 将处理过的tokens重新组合成SQL语句
    result_sql = ''.join(str(token) for token in new_tokens).strip()
    
    return result_sql


# 这段代码的for循环有问题，没有真正支持多个非结构化字段的语义，比如 内容描述 like '支付宝平台' or 案件描述 like '支付宝平台'
async def sql_semantic_rewrite(sql_command: str, milvus_opt, unstr_dict: dict, unstructured_column: str, chain: Runnable, app_retrieve: Runnable):

    parameters = {}
    # 如果里面包含了非结构化字段，则执行语义的检索
    for ori_cmd, unstr in unstr_dict.items():  
        # 对非结构化的值判断是否为命名实体，如果是的话就不必执行非结构化检索了
        ner_result = chain.invoke({'input': unstr})
        logger.info(f"{unstr} 的命名实体判别： {ner_result.binary_score}")
        if ner_result.binary_score == 'yes':
            continue
        
        # 这个graph是没有query的，因为传递数据不需要处理它
        final_state = await app_retrieve.ainvoke(
            {
            "unstr_value": unstr,
            "filter_exp": '',
            "milvus_opt": milvus_opt
            }
        ) # 为了加速检索的过程，filter_exp 可以不为空，需要把四级分类的条件写进去，或者把其他条件也写进去
    
        unstr_values = final_state['documents']
        placeholders = ', '.join([f":val{i}" for i in range(len(unstr_values))]) 
        sql_command = sql_command.replace(ori_cmd, f""" `{unstructured_column}` IN ({placeholders})""")
        # 构建parameters字典，将每个值映射到其对应的命名参数
        parameters = {f"val{i}": value for i, value in enumerate(unstr_values)}
    
    return sql_command, parameters



def keyword_matching(substring, main_strings):
    """
    查找并返回main_strings中所有包含substring所有字符的字符串。
    
    :param substring: 子串
    :param main_strings: 主字符串列表
    :return: 包含所有匹配成功的主字符串的列表
    """
    def check_all_chars_in_string(substring, main_string):
        for char in substring:
            if char not in main_string:
                return False
        return True

    matching_strings = []
    for main_string in main_strings:
        if check_all_chars_in_string(substring, main_string):
            matching_strings.append(main_string)

    return matching_strings


async def sql_abbr_rewrite(sql_command: str,  abbr_dict: dict, abbreviation_column: str, full_abbr_values: list, total_len=0):
    """
    将sql中某写列是涉及缩写的，找出来替换成 满足缩写匹配条件的字段值
    """
    parameters = {}
    
    for ori_cmd, abbr_str in abbr_dict.items():  
        # 对非结构化的值判断是否为命名实体，如果是的话就不必执行非结构化检索了
    
        print(abbr_str, full_abbr_values)
        abbr_values = keyword_matching(abbr_str, full_abbr_values)
        print(f'缩写字段值{abbr_str} match 的全文为： {abbr_values}')
        placeholders = ', '.join([f":val{i + total_len}" for i in range(len(abbr_values))]) 
        sql_command = sql_command.replace(ori_cmd, f""" `{abbreviation_column}` IN ({placeholders})""")
        
        each_parameters = {f"val{i + total_len}": value for i, value in enumerate(abbr_values)}
        parameters.update(each_parameters)

        total_len += len(abbr_values)
    
    return sql_command, parameters



def sql_execute(mysql_db, sql_command: str, schema: str,  params: dict, sql_rewrite_chain: Runnable,):

    try:
        if len(params) != 0:
            try:
                logger.info(f'sql 语句：{sql_command}')
                # logger.info(f'params: {params}')
                
                sql_result = mysql_db.run(sql_command, include_columns=True, parameters=params)
            except Exception as e :
                sql_result = ''
                logger.error(f'execute sql with seme wrong: {e}', exc_info=True)
        else:
            sql_result = mysql_db.run(sql_command, include_columns=True)
            
    except Exception as e:
        if config.is_semantic_analysis or config.is_abbr_analysis:
            print('sql 执行错误，语义分析/缩写分析不支持sql重写')
            return ''
        new_sql_command_result = sql_rewrite_chain.invoke({"schema": schema, "old_sql": sql_command, 'error': e})
        new_sql_command = new_sql_command_result.sql
        try:
            if len(params) != 0:
                sql_result = mysql_db.run(new_sql_command, include_columns=True, parameters=params)
            else:
                sql_result = mysql_db.run(sql_command, include_columns=True)
        except:
            sql_result = ''  #在 SQLDatabase 中存在'[xxx]'，与 '' 两种
    
    return sql_result



def datetime_parser(query: str, text2datetime_chain: Runnable):

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    start_time = time.time()
    generation = text2datetime_chain.invoke({"query": query, "now": now})
    res = generation.create_time

    # 将大模型输出的datetime格式进行格式化
    start_time = res[0].strftime("%Y-%m-%d %H:%M:%S")
    end_time = res[1].strftime("%Y-%m-%d %H:%M:%S")

    return start_time, end_time 


def generation_filter_expr(milvus_field_type: dict, condition_columns: dict, unstructured_column: str, ner_clf_chain: Runnable, text2datetime_chain: Runnable):

    # 确定非结构化字段的查询
    unstructrued_value = condition_columns[unstructured_column] if \
              unstructured_column in condition_columns else ''
        
    expr_list = []       
    for field, value in condition_columns.items():
        columns_field_en = config.columns_map[field]
        # 非结构化字段单独处理
        if field == unstructured_column: # 非结构化字段不参与
            ner_result = ner_clf_chain.invoke({'input': value})
            if ner_result.binary_score == 'yes':
                expr_list.append(f"""{columns_field_en} like '%{value}%' """)
                unstructrued_value = ''
            continue
        
        if milvus_field_type[columns_field_en] == 'VARCHAR' and field not in config.datetime_type_field:
            expr_list.append(f"""{columns_field_en} like '%{value}%' """)

        elif field in config.datetime_type_field:
            start_time, end_time = datetime_parser(value, text2datetime_chain)
            datetime_exp = f""" ('{start_time}' < {columns_field_en} < '{end_time}') """
            expr_list.append(datetime_exp)
        else:
            print('{} 对应的数据类型目前还不支持处理'.format(field))  # 数字还不能处理
        
    filter_exp = ' and '.join(expr_list)  # 也有可能是OR，这里暂且是and

   
    return filter_exp, unstructrued_value



def params_parser(param_db, metadata_table_name, data_table_name):
    # 重新获取表结构
    sql_cmd = f"""SELECT * FROM `{metadata_table_name}` """
    try:
        result = param_db.run(sql_cmd,include_columns=True)  
    except Exception as e:
        logger.info(f"获取表 {metadata_table_name} 的元数据失败: {e}")
        return '', [], [], {}

    if result == '':
        logger.info(f"没有找到表 {metadata_table_name} 的元数据")
        
    # 获取对应表的元数据
    full_meta_data_list = eval(result) 
    meta_data_list = [i for i in full_meta_data_list if i['table_name'] == data_table_name]
    # 生成Schema信息
    schema_list = []
    
    start_str = f"CREATE TABLE `{data_table_name}` ("
    schema_list.append(start_str)
    for field_meta_data in meta_data_list:
        meta_data_str = f"""`{field_meta_data['field_name']}` {field_meta_data['field_type']}; {field_meta_data['field_comment']}; {field_meta_data['data_example']}"""
        schema_list.append(meta_data_str)
    end_str = f""") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci """
    
    schema_list.append(end_str)
    schema = '\n'.join(schema_list)

    # 判断是否有缩写
    abbr_columns = [each_data['field_name'] for each_data in meta_data_list if each_data['is_abbr_dim'] == 1] 
    # 获取关联字段的列表
    related_columns = [each_data['field_name'] for each_data in meta_data_list if each_data['is_search_dim'] == 1]
    # 获取字段映射表
    filed_mapping = {each_data['field_name']: each_data['english_name'] for each_data in meta_data_list}

    return schema, abbr_columns, related_columns, filed_mapping




def get_enum_values(
    mysql_db,
    table_name: str,
    max_distinct_values_num: int = 1000, 
    max_combined_values_length: int = 5000,
    LIMIT: int = 10000):
    
    """
    获取表中所有可能的枚举字段及其值（并发版本）
    """
    random.seed(42)

    try:
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
        sample_values = {}

        def process_column(column_info):
            column_name = column_info[0]
            data_type = column_info[1]
            print(f"Processing column (in thread): {column_name}, data_type: {data_type}")

            if data_type.lower() not in ['enum', 'char', 'varchar', 'text', 'longtext', 'bool', 'boolean',
                                         'tinyint', 'int', 'bigint']:
                return None, None, None # Skip non-enum types

            distinct_query = f"""
                SELECT DISTINCT `{column_name}`
                FROM `{table_name}` 
                WHERE `{column_name}` IS NOT NULL 
                LIMIT {LIMIT}
            """

            try:
                distinct_values = mysql_db.run(distinct_query)
                distinct_values = eval(distinct_values)
                distinct_values = [v[0] for v in distinct_values]

                combined_length = sum(len(str(v)) for v in distinct_values)

                if len(distinct_values) <= max_distinct_values_num and combined_length <= max_combined_values_length:
                    return column_name, sorted(distinct_values), None
                else:
                    samples = random.sample(distinct_values, k=min(3, len(distinct_values)))
                    return column_name, None, samples

            except Exception as e:
                logger.debug(f"Error processing column {column_name}: {str(e)}")
                return column_name, None, None

        with ThreadPoolExecutor() as executor:
            future_to_column = {
                executor.submit(process_column, column_info): column_info
                for column_info in columns_result
            }

            for future in as_completed(future_to_column):
                result = future.result()
                col_name, enum_list, sample_list = result

                if enum_list is not None:
                    enum_values[col_name] = enum_list
                    logger.info(f"Found enum field: {col_name} with {len(enum_list)} values")
                elif sample_list:
                    sample_values[col_name] = sample_list

        return enum_values, sample_values

    except Exception as e:
        logger.error(f"Error in get_enum_values: {str(e)}")
        return {}, {}
    

def get_distinct_values(
    mysql_db,
    table_name: str,
    column_list: list, 
    LIMIT: int = 100000):
    """
    获取表中制定列名的枚举值
    """
    result = {}
    for column_name in column_list:
        distinct_query = f"""
            SELECT DISTINCT `{column_name}`
            FROM `{table_name}` 
            WHERE `{column_name}` IS NOT NULL 
            LIMIT {LIMIT}
        """

        distinct_values = mysql_db.run(distinct_query, include_columns=True)
        distinct_values = eval(distinct_values)
        dist_dict =  {column_name: [d[column_name] for d in distinct_values]}
        result.update(dist_dict)
    
    # result: {'事项名称': [x, x, x], 'xx': [x, x, x,]}
    return result
                


if __name__ == '__main__':

    # param_db = SQLDatabase.from_uri(config.param_uri,)
    # metadata_table_name = config.param_table_metadata
    # search_table_name = config.param_table_search

    # data_table_name = config.data_table_names[0]

    # # schema, abbr_columns, related_columns, field_mapping = params_parser(param_db, metadata_table_name, data_table_name)
    # # print(schema, abbr_columns, related_columns, field_mapping)

    # enum_values, _ = get_enum_values(param_db, search_table_name, config.max_distinct_values_num, config.max_combined_values_length)
    # print(enum_values)

    '''mysql_db = SQLDatabase.from_uri(config.mysql_uri,)  
    get_distinct_values(mysql_db, 'hongkou', ['事项大类', '事项小类', '事项标签'])'''

    query = '城市管理类'
    emb_1 = embedding_bge("投诉类、咨询类、建议类").reshape(1, -1)
    emb_2 = embedding_bge("咨询类").reshape(1, -1)
    '''with open('./metadata/related_values_shanghai_ad_time.json', 'r', encoding='utf-8') as f:
        related_values = json.loads(f.read())'''
    # key, value = retrieve_cases_full(query=query, related_values=related_values)
    result = cosine_similarity(emb_1, emb_2)[0][0]
    print(result)