from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain.schema.runnable import Runnable
import re 
import os 
import logging 
import time 
# from configs import config as config

def create_str_chain(model, prompt) -> Runnable :

    # Create the generate chain
    generate_chain = prompt | model | StrOutputParser()

    return generate_chain


def create_json_chain(model, prompt):

    # Create the generate chain
    generate_chain = prompt | model | JsonOutputParser()

    return generate_chain



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

# log_dir = config.log_dir
log_dir = '/data/liyiru/WiSearch/new/app/logs'
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
