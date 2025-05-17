import os
import json
from configs import config
from module.prompt import *
from models.langchain_models import llm_qwen_14B
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import Runnable
from schema_linking.meta_dict_gen import meta_data_gen
from schema_linking.few_linking_gen import samples_gen
from schema_linking.related_col_find import get_distinct_values
from module.structured_output import create_str_chain, create_json_chain



def init(query_list=[], meta_data_chain: Runnable = None, is_meta_data=True, is_schema_linking_gen=True, is_distinct_values_gen=True):

    #step1 生成元数据
    schema_list = []
    if is_meta_data:
        for table_name in config.table_names:
            file_path = os.path.join(config.data_save_dir, f'{table_name}_meta_data.txt')    
            schema_gen, is_True = meta_data_gen(config.mysql_uri, table_name, meta_data_chain, is_supplement=True)
            assert is_True, '元数据生成失败, 生成的字段不一致'
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(schema_gen)
                schema_list.append(schema_gen) 
            
    else: # 如果元数据已经存在，则直接读取
        for table_name in config.table_names:
            file_path = os.path.join(config.data_save_dir, f'{table_name}_meta_data.txt')
            with open(file_path, 'r', encoding='utf-8') as f:
                schema_list.append(f.read())
        
    # step2生成schema linking的样例数据
    if not query_list:
        schema_linking_samples = []

    elif is_schema_linking_gen:
    
        file_path = os.path.join(config.data_save_dir, 'schema_linking_samples.json')
        # schema linking samples generation
        prompt_samples_gen = PromptTemplate(template=schema_link_prompt, input_variables=["schema", "query", 'samples'])
        linking_chain = create_json_chain(prompt_samples_gen, llm_qwen_14B)
        schema_linking_samples = samples_gen(query_list, '\n'.join(schema_list), linking_chain)
        # Check if file exists and merge with existing samples
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_samples = json.load(f)
                # Merge existing and new samples, avoiding duplicates
                merged_samples = existing_samples
                for sample in schema_linking_samples:
                    if sample not in existing_samples:
                        merged_samples.append(sample)
                schema_linking_samples = merged_samples

        # Write merged samples back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(schema_linking_samples, f, ensure_ascii=False, indent=4)
    else:
    
        file_path = os.path.join(config.data_save_dir, 'schema_linking_samples.json')
        with open(file_path, 'r', encoding='utf-8') as f:
            schema_linking_samples = json.load(f)

    # step3 生成related columns的distinct values 
    if is_distinct_values_gen:
        for table_name in config.table_names:
            file_path = os.path.join(config.data_save_dir, f'{table_name}_distinct_values.json')
            distinct_values = get_distinct_values(config.mysql_uri, table_name, config.related_columns)
            # 如果distinct_values不为空，则保存到文件
            if distinct_values:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(distinct_values, f, ensure_ascii=False, indent=4)
    else:
        for table_name in config.table_names:
            file_path = os.path.join(config.data_save_dir, f'{table_name}_distinct_values.json')
            if not os.path.exists(file_path): # 如果多表，则只有一个表有distinct_values
                continue
            with open(file_path, 'r', encoding='utf-8') as f:
                distinct_values = json.load(f)


    return schema_list, schema_linking_samples, distinct_values
