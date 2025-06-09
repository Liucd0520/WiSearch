from sql_processing.text2sql import  sql_gen
from langchain.schema.runnable import Runnable
from sql_processing.view_manager import create_temp_view, sql_replace_view, drop_view
from utils.util import sql_semantic_rewrite, sql_execute, sql_abbr_rewrite
from configs import config as config
from utils.util import *
from decimal import Decimal


async def sql_path(query: str, mysql_db, linking_columns: dict, schema: str, view_values: str, 
            sql_gen_chain: Runnable,  sql_feedback_chain: Runnable, 
            abbr_column: str = '', full_abbr_values:list = [],
            unstructured_column: str = '', ner_clf_chain: Runnable = None, app_retrieve: Runnable=None, milvus_opt=None):
    
    sql_result = {}
    sql_command = sql_gen(query, linking_columns, schema, sql_gen_chain)
    sql_result.update({'sql_std': sql_command})
    logger.info(f"stad sql: {sql_command}")

    sementic_params = {}  # 初始化参数，仅当处理非结构化字段时使用
    if config.is_semantic_analysis and unstructured_column: # unstructured_column 是表里是否有非结构化字段，不是看抽取的内容里是否有非结构化字段
        # 可能会有语义分析，取决于是否有sql语句中是否含义非结构化字段信息
        unstr_dict = unstructure_value_extract(sql_command, unstructured_column)  
        logger.info(f'非结构化信息为: {unstr_dict}')
        if not unstr_dict:
            logger.info('sql查询命令中没有非结构化信息则不进行语义分析')
        else:
            logger.info(f'开始语义分析 ..  .. ')
            # 字典格式（可能存在多个kv对）：{"`案件描述/内容描述` LIKE '%支付宝平台%';": '支付宝平台'}
            # 如果unstr_dict 为空，语义分析依然能够正常处理
            sql_command, sementic_params = await sql_semantic_rewrite(sql_command, milvus_opt, unstr_dict, unstructured_column,  ner_clf_chain, app_retrieve)
            sql_command_semantic = sql_command
            sql_result.update({'sql_sementic': sql_command_semantic})
    
    abbr_params = {}  # 初始化参数，仅当处理缩写列字段时使用
    if config.is_abbr_analysis and abbr_column: 
        logger.info(f'开始缩写分析 ... ')
        
        abbr_dict = unstructure_value_extract(sql_command, abbr_column)    
        logger.info(f'要被缩写的字段信息为: {abbr_dict}')
        
        sql_command, abbr_params = await sql_abbr_rewrite(sql_command, abbr_dict, abbr_column, full_abbr_values,  total_len=len(sementic_params))
        sql_command_abbr = sql_command
        sql_result.update({'sql_abbr': sql_command_abbr})


    # 基于视图的查询
    view_table_names = []
    for table_name in config.data_table_names:
        view_table_name = create_temp_view(mysql_db, table_name, 
                                            config.view_index,  view_values)
        if view_table_name:
            sql_command = sql_replace_view(sql_command, table_name, view_table_name)
            view_table_names.append(view_table_name)
            logger.info(f'视图为： {view_table_name}')
    
    if len(view_table_names) == 0:
        logger.info(f"没有找到< {view_values} >对应的视图")
    sql_command_view = sql_command
    sql_result.update({'sql_view': sql_command_view})
    
    
    params = sementic_params | abbr_params
    # 执行sql查询
    execute_result = sql_execute(mysql_db, sql_command, schema, params, sql_feedback_chain)
    obtain_data = eval(execute_result) if  execute_result != '' else [{}]
    
    # 执行完sql之后删除视图
    drop_view(mysql_db, view_table_names)

    return obtain_data, sql_result, params
