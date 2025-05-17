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
from datetime import datetime
from configs import config



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
    print(conditions)

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


async def sql_abbr_rewrite(sql_command: str,  abbr_dict: dict, abbreviation_column: str, ):
    """
    将sql中某写列是涉及缩写的，找出来替换成 满足缩写匹配条件的字段值
    """
    parameters = {}
    total_len = 0 
    for ori_cmd, abbr_str in abbr_dict.items():  
        # 对非结构化的值判断是否为命名实体，如果是的话就不必执行非结构化检索了
        import json 
        with open(f'gjw_distinct_values.json', 'r', encoding='utf-8') as f:
            full_list = json.load(f)

        abbr_values = keyword_matching(abbr_str, full_list)
       
        placeholders = ', '.join([f":val{i + total_len}" for i in range(len(abbr_values))]) 
        sql_command = sql_command.replace(ori_cmd, f""" `{abbreviation_column}` IN ({placeholders})""")
        
        each_parameters = {f"val{i + total_len}": value for i, value in enumerate(abbr_values)}
        parameters.update(each_parameters)

        total_len += len(abbr_values)
    
    return sql_command, parameters



def sql_execute(mysql_uri: str, sql_command: str, schema: str,  params: dict, sql_rewrite_chain: Runnable,):
    # print('sql command --> ', sql_command)
    import time 
    start_time = time.time()
    mysql_db = SQLDatabase.from_uri(mysql_uri)
    print(time.time() - start_time)
    try:
        if len(params) != 0:
            try:
                # print('params', params)
                sql_result = mysql_db.run(sql_command, include_columns=True, parameters=params)
            except Exception as e :
                logger.info(f'execute sql with seme wrong: {e}')
        else:
            sql_result = mysql_db.run(sql_command, include_columns=True)
            
    except Exception as e:
        if config.is_semantic_analysis:
            print('sql 执行错误，语义分析不支持sql重写')
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



if __name__ == '__main__':

    sql_query = "SELECT COUNT(`案件编号`) AS `扰民事件数量` FROM `HongKouDemo` WHERE `发现时间` LIKE '2024-08%' AND `案件描述/内容描述` LIKE '%扰民%';"
    result = unstructure_value_extract(sql_query, '案件描述/内容描述')
    print(result)
