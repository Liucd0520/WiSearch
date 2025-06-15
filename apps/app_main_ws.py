
from pathlib import Path
import sys 
import os 
import json
# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)


from models.langchain_models import llm_qwen_14B
from utils.util import *
from sql_processing.text2sql import schema_linking, sql_gen
from configs import config as config
from langchain_community.utilities import SQLDatabase
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter, FastAPI
import os
from module.prompt import *
from models.langchain_models import llm_qwen_14B
from utils.util import *
from sql_processing.text2sql import schema_linking, sql_gen
from configs import config as config
from langchain_community.utilities import SQLDatabase
from module.main_llm import *
from online_sql import sql_path
from models.create_chain import *
import simplejson
import uvicorn
from fastapi import FastAPI, WebSocket
from webui_models.utils import query_insight_generator, obtain_detail_data
from apps.websocket_manager import clients
from apps.websocket_manager import send_to_clients
from pymilvus import MilvusClient
from operator_workflow.milvus_client import MilvusOperation
from operator_workflow.workflow import app_retrieve, app_retrieve_extraction, app_retrieve_summary
import datetime

app = FastAPI()

app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
) # 中间件白名单



class ObtainDataItem(BaseModel):
    query: str = '近1年哪些小区有设备维修的需求'

# WebSocket路由
@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    clients.append(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            print(message)
            data = json.loads(message)
            # 使用 Pydantic 模型验证输入
            validated_data = ObtainDataItem(**data)
            query = validated_data.query
            view_values = '' # 暂且不设置视图

            logger.info('案例库查询')
            top_indices = retrieve_cases(query=query, embedding_corpus=embedding_corpus)
            select_case_list = [corpus[i]  for i in top_indices]
            filtered_list = [str(item) for item in examples if item['query'] in select_case_list]
            logger.info(f'案例库查询结果: {filtered_list}')


            new_linking_columns = schema_linking(query, schema, related_columns, distinct_values, 
                                         examples='\n'.join(filtered_list), chain=schema_linking_chain)
            logger.info(f"schema linking: {new_linking_columns}")

            target_columns = new_linking_columns['target_columns']
            condition_columns = new_linking_columns['condition_columns']
            
            # 调用流式生成器并实时传输数据
            async for chunk in query_insight_generator(explanation_chain, query, schema, new_linking_columns):
                # logger.info(chunk)
                await websocket.send_text(chunk)  # 将每个 chunk 发送给客户端
            
                
            task_type = 'SQL'
            # 判断查询列是否在结构化字段里
            if  related_columns in target_columns: 
                # 意味着可能需要语义分析
                res = task_aware_chain.invoke({'query': query, })
                task_type = res['TaskType']
            logger.info(f'任务类型: {task_type}')

            if task_type in ['SQL', '内容分类']: 
            
                obtain_data, sql_result, params = await sql_path(query, mysql_db, new_linking_columns, schema, view_values, 
                                                                 sql_gen_chain,  sql_feedback_chain, abbr_columns[: 0], full_abbr_values,
                config.unstructrued_column, ner_clf_chain, app_retrieve, milvus_opt
                )
                
                # 将生成的候选sql 查询语句发生给前端
                try:
                    await send_to_clients(json.dumps({"sql_gen": sql_result['sql_std']}, ensure_ascii=False))
                except Exception as e:
                    logger.info(f'sql_gen 发送失败: {e}')
                
            elif task_type in ['内容抽取', '内容总结']:
                # 生成filter_exp (会过滤掉非 结构化字段)
                filter_expr, unstructrued_value = generation_filter_expr(milvus_field_type, condition_columns, config.related_columns[-1], 
                                                                        ner_clf_chain, text2datetime_chain, )  
                logger.info(f'过滤表达式： {filter_expr}; 查询问题： {unstructrued_value}')
                # 执行
                if task_type == '内容总结':
                    final_state = await app_retrieve_summary.ainvoke(
                        {"unstr_value": unstructrued_value, "filter_exp":  filter_expr, "milvus_opt": milvus_opt})
                    
                elif task_type == '内容抽取':
                    final_state = await app_retrieve_extraction.ainvoke(
                        { 'query': query, "unstr_value": unstructrued_value, "filter_exp":  filter_expr,"milvus_opt": milvus_opt})
                        # [{"企业": "孔乙己酒家", "数量": 2}, {}, {}]
                obtain_data = final_state['outputs'] 
            else:
                print('{} 任务类型目前还不支持处理'.format(task_type))
                
            # 将查询问题所对应的结果发送给前端
            try:    
                def custom_serializer(obj):
                    if isinstance(obj, (datetime.datetime,datetime.date) ):
                        return obj.isoformat()
                    raise TypeError(f"Type {type(obj)} not serializable")
                print('obtain_data --> ', obtain_data)
                await send_to_clients(json.dumps({"response": obtain_data}, default=custom_serializer, ensure_ascii=False))
            except Exception as e:
                logger.error(f'response 发送失败: {e}')

            # 获取数据明细
            # 将与结果相关的数据明细发送给前端
            if task_type in ['SQL', '内容分类']:
                pattern = r"(?i)(SELECT\s+)(.*?)(\s+FROM)"
                modified_sql = re.sub(pattern, lambda match: f"{match.group(1)}*{match.group(3)}", sql_result['sql_view'], flags=re.IGNORECASE)
                modified_sql_group_remove = remove_group_by(modified_sql)
                execute_result = sql_execute(mysql_db, modified_sql_group_remove, schema, params, sql_feedback_chain)
                result_detail = eval(execute_result) if  execute_result != '' else [{}]
            else: 
                result_detail = [{}] 
            try:
                # print('xx.>',result_detail)
                await send_to_clients(simplejson.dumps({"data_detail": result_detail[:1000]}, 
                                                default=str,ensure_ascii=False))  # 会把datatime转成字符串，另外一种是把result_detail转换字符串: str(result_detail)
                print('发生成功')
            except Exception as e:
                logger.info(f'data_detail 发送失败: {e}')
    
            # 将对结果的解读发送给前端
            TopK_data = obtain_data[:15]
            result_insight = chat_chain.invoke({ "query": query, "obtain_data": TopK_data})
            try:
                await send_to_clients(json.dumps( {"result_insight": result_insight}, ensure_ascii=False))
            except Exception as e:
                logger.info(f'result_insight 发送失败: {e}')
            
            # 将接下来的推荐问题发生给前端
            query_recommands = recommand_chain.invoke({ "query": query, "schema": schema, "obtain_data": TopK_data})
            try:    
                await send_to_clients(json.dumps({"result_recommand": query_recommands}, ensure_ascii=False))
            except Exception as e:
                logger.info(f'result_recommand 发送失败: {e}')
            
            logger.info('query: {query} 处理完毕')
    except Exception as e:
        # 出现错误时，移除客户端连接
        logger.error(f'Unexpected error occured:{e}', exc_info=True)
        clients.remove(websocket)



if __name__ == '__main__':
    
    mysql_db = SQLDatabase.from_uri(config.mysql_uri)
    param_db = SQLDatabase.from_uri(config.param_uri)
    
    if not os.path.exists(config.data_save_dir):
        os.makedirs(config.data_save_dir)
    if not os.path.exists(config.log_dir):
        os.makedirs(config.log_dir)
    
    gen_query_list = []
    
    # # 获取某个表的元数据获取
    # schema, abbr_columns, related_columns, columns_map = \
    #     params_parser(param_db, config.param_table_metadata, config.data_table_names[0])
    
    
    abbr_columns = []
    columns_map = config.columns_map 
    related_columns = ['一级分类', '二级分类', '三级分类', '四级分类',]
    schema = """
    CREATE TABLE shanghai (
        `工单编号` BIGINT; 含义: 表示工单的唯一编号。; 用途: 用于唯一标识每个工单，便于查询和管理。; 示例值: 20240101000072; 备注: 无;
        `工号` BIGINT; 含义: 表示工单的生成编号。; 用途: 用于记录工单的生成顺序，便于排序和统计。; 示例值: 3830; 备注: 无;
        `工单生成时间` DATETIME; 含义: 表示工单的生成时间。; 用途: 用于记录工单的生成时间，便于时间维度的管理和分析。; 示例值: 2024-01-01 00:37:39; 备注: 无;
        `诉求地址` TEXT; 含义: 表示工单所涉及的具体地点的详细地址。; 用途: 提供工单发生地点的详细信息，便于定位和处理。; 示例值: "闵行区东川路555弄"; 备注: 无;
        `诉求区域` TEXT; 含义: 表示工单所涉及的具体地点所属的行政区。; 用途: 用于快速定位工单发生的区域，便于区域级别的管理和调度。; 枚举类型，值包括： "黄浦区", "徐汇区", "长宁区", "静安区",  "普陀区", "虹口区", "杨浦区", "闵行区", "宝山区", "嘉定区", "浦东新区", "金山区",  "松江区", "青浦区","奉贤区", "崇明区"; 备注: 无;
        `内容描述` TEXT; 含义: 对工单所涉及的具体问题的详细描述。; 用途: 提供完整的信息，帮助处理人员全面了解问题背景和具体情况。; 示例值: "市民来电反映:未成年游戏充值要求退费，心动网络有限公司旗"; 备注: 无;
        `工单类别` TEXT; 含义: 表示工单紧急程度的类别。; 用途: 用于对工单紧急程度分级，便于管理和迅速响应。; 枚举类型，包含: "一般", "次紧急", "紧急"; 备注: 无;
        `处理描述` TEXT; 含义: 对工单处理结果的描述。; 用途: 记录工单的处理情况，便于后续查询和分析。; 示例值: "市民反复催单，已电子催单工单编号：20231224019374，故归档。"; 备注: 无;
        `客户类型` TEXT; 含义: 表示工单客户的类型。; 用途: 用于区分不同类型的客户，便于管理和服务。; 枚举类型，包含 "个人", "企业"; 备注: 无;
        `一级分类` TEXT; 含义: 表示工单所属的最高级别的分类。; 用途: 用于快速定位和分类工单，便于管理和统计。;枚举类型，包括： "科教文卫类", "社会管理类", "公安政法类", "其他类", "建设交通类",  "公用事业类", "安全监管类", "经济综合类", "社会团体类"; 备注: 无;
        `二级分类` TEXT; 含义: 在一级分类之下，更具体的分类。; 用途: 进一步细化工单分类，提高管理精度。; 示例值: "文广影视"; 备注: 无;
        `三级分类` TEXT; 含义: 在二级分类之下，更加具体的分类。; 用途: 提供更详细的分类信息，方便具体问题的处理和跟踪。; 示例值: "文化产业管理"; 备注: 无;
        `四级分类` TEXT; 含义: 在三级分类之下，更加具体的分类。; 用途: 提供更详细的分类信息，方便具体问题的处理和跟踪。; 示例值: "游戏动漫"; 备注: 无;
        `主办单位` TEXT; 含义: 表示工单的主办单位。; 用途: 用于记录工单的主办单位，便于管理和协调。; 示例值: "市文化旅游局", "市公安局", "普陀区人民政府"; 备注: 无;
        `是否匿名` TEXT; 含义: 表示工单是否为匿名工单。; 用途: 用于区分匿名工单和非匿名工单，便于管理和保护隐私。; 示例值: "是"; 备注: 无;
        `服务类型` TEXT; 含义: 表示工单的服务类型。; 用途: 用于分类工单的服务类型，便于管理和统计。; 枚举类型，包括: "综合服务", "一网通办"; 备注: 无;
        `通话编号` TEXT; 含义: 表示工单的通话编号。; 用途: 用于记录工单的通话记录，便于查询和分析。; 示例值: "1704040581-2297011"; 备注: 无;
        `工单类型` TEXT; 含义: 表示工单的类型。; 用途: 用于分类工单的类型，便于管理和统计。; 枚举类型，包括: "求助类", "投诉举报类", "咨询类", "意见建议类", "其他类"; 备注: 无;
        `新一级分类` TEXT; 含义: 表示工单的新一级分类。; 用途: 用于记录工单的新分类信息，便于管理和统计。; 示例值: "None"; 备注: 无;
        `新二级分类` TEXT; 含义: 表示工单的新二级分类。; 用途: 用于记录工单的新分类信息，便于管理和统计。; 示例值: "None"; 备注: 无;
        `新三级分类` TEXT; 含义: 表示工单的新三级分类。; 用途: 用于记录工单的新分类信息，便于管理和统计。; 示例值: "None"; 备注: 无;
        `新四级分类` TEXT; 含义: 表示工单的新四级分类。; 用途: 用于记录工单的新分类信息，便于管理和统计。; 示例值: "None"; 备注: 无;
        `新五级分类` TEXT; 含义: 表示工单的新五级分类。; 用途: 用于记录工单的新分类信息，便于管理和统计。; 示例值: "None"; 备注: 无;
    )DEFAULT CHARSET=utf8mb4 ENGINE=InnoDB COLLATE utf8mb4_0900_ai_ci
    """

    logger.info(f'获取的表元数据: {schema}')
    logger.info(f'获取的缩写列: {abbr_columns}')
    logger.info(f'获取的关联列: {related_columns}')
    logger.info(f'获取的列映射: {columns_map}')

    # 获取关联字段的值
    distinct_values = get_distinct_values(mysql_db, config.data_table_names[0], related_columns)
    # 获取缩写列的所有枚举值
    full_abbr_dict = get_distinct_values(mysql_db, config.data_table_names[0], abbr_columns)
    if abbr_columns:
        full_abbr_values = full_abbr_dict[abbr_columns[0]] # 只有其中一个是有值的
    else:
        full_abbr_values = []

    logger.info(f'关联字段的枚举值:  {distinct_values}')
    logger.info(f"缩写字段的枚举值： {full_abbr_values}")
    
    # 案例库：
    with open(f'examples_{config.data_table_names[0]}.json', 'r', encoding='utf-8') as f_json:
        examples = json.load(f_json)
    
    # 案例库的语料
    corpus = [each_data['query'] for each_data in examples]
    embedding_corpus = embedding_bge(corpus)


    milvus_opt = MilvusOperation(uri=config.uri, collection_name= config.collection_name, bm25_ef_path=config.bm25_ef_path)
    client = MilvusClient(uri=config.uri)
    collection_info = client.describe_collection(collection_name=config.collection_name)
    # 'fields': [{'field_id': 100, 'name': 'id', 'description': '', 'type': <DataType.INT64: 5>, 'params': {}, 'is_primary': True}, ]
    milvus_field_type = {each_field['name']: each_field['type'].name for each_field in collection_info['fields']} # <DataType.INT64: 5> ==> .name, .value 获取枚举类型的数据
    # {'id': 'INT64'}

    uvicorn.run(app=app, host='0.0.0.0', port=33063 )

