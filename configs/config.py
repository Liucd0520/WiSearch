# mysql_uri = 'mysql+mysqlconnector://sh12333_znrpt:Znrpt14!$@10.218.0.3:3324/sh_12333_znrpt'
mysql_uri = 'mysql+mysqlconnector://chatbi:IDEAL@172.31.24.111:3307/shanghai'
param_uri = 'mysql+mysqlconnector://root:liucd123@172.31.24.111:3307/xingchentwo'  # !!

data_table_names = ['znrpt_cuv_summary_gd_extend', ]
param_table_metadata = 'field_metadata'    # !!

# milvus
collection_name = 'collection_12333'
uri = 'http://10.218.1.3:19535'

primary_key_name = 'id'

is_semantic_analysis = True 
unstructrued_column = 'content'
large_step = 100
small_step = 10 
window_size = 50 
min_sample = 5
extend_field = ''
limit = 5000 


is_abbr_analysis = False 


# 保存路径
log_dir = './logs'
data_save_dir = './data_12333'
bm25_ef_path='data_12333/12333_bm25.json'

# 枚举值参数
max_distinct_values_num = 100
max_combined_values_length = 1000
# 视图索引 控制不同的查询权限
view_index = ''
# 字符串类型里哪些是有datetime类型的字段
datetime_type_field = []

# 中英文字段对照
columns_map = {'content': 'content',
 'cuv_biztype1': 'cuv_biztype1',
 'cuv_biztype1_cn': 'cuv_biztype1_cn',
 'cuv_biztype2': 'cuv_biztype2',
 'cuv_biztype2_cn': 'cuv_biztype2_cn',
 'cuv_biztype3': 'cuv_biztype3',
 'cuv_biztype3_cn': 'cuv_biztype3_cn',
 'cuv_biztype4': 'cuv_biztype4',
 'cuv_biztype4_cn': 'cuv_biztype4_cn',
 'cuv_biztype5': 'cuv_biztype5',
 'cuv_biztype5_cn': 'cuv_biztype5_cn',
 'cuv_biztype6': 'cuv_biztype6',
 'cuv_biztype6_cn': 'cuv_biztype6_cn',
 'cuv_biztype7': 'cuv_biztype7',
 'cuv_biztype7_cn': 'cuv_biztype7_cn',
 'cuv_call_type': 'cuv_call_type',
 'cuv_call_type_cn': 'cuv_call_type_cn',
 'cuv_channel': 'cuv_channel',
 'cuv_channel_cn': 'cuv_channel_cn',
 'cuv_contact_tel': 'cuv_contact_tel',
 'cuv_customer_id': 'cuv_customer_id',
 'cuv_customer_name': 'cuv_customer_name',
 'cuv_customer_type': 'cuv_customer_type',
 'cuv_customer_type_cn': 'cuv_customer_type_cn',
 'cuv_deal_scheme': 'cuv_deal_scheme',
 'cuv_district': 'cuv_district',
 'cuv_district_cn': 'cuv_district_cn',
 'cuv_identity': 'cuv_identity',
 'cuv_identity_cn': 'cuv_identity_cn',
 'cuv_qes_desc': 'cuv_qes_desc',
 'cuv_replay_account': 'cuv_replay_account',
 'cuv_session_id': 'cuv_session_id',
 'cuv_solved': 'cuv_solved',
 'cuv_solved_cn': 'cuv_solved_cn',
 'cuv_start_time': 'cuv_start_time',
 'cuv_summary_type': 'cuv_summary_type',
 'cuv_summary_type_cn': 'cuv_summary_type_cn',
 'extend_call_matter': 'extend_call_matter',
 'extend_call_matter_cn': 'extend_call_matter_cn',
 'extend_commend_category': 'extend_commend_category',
 'extend_commend_category_cn': 'extend_commend_category_cn',
 'gd_back_flag': 'gd_back_flag',
 'gd_back_flag_cn': 'gd_back_flag_cn',
 'gd_call_id': 'gd_call_id',
 'gd_call_no': 'gd_call_no',
 'gd_call_time': 'gd_call_time',
 'gd_call_type': 'gd_call_type',
 'gd_call_type_cn': 'gd_call_type_cn',
 'gd_channel_typeid': 'gd_channel_typeid',
 'gd_channel_typeid_cn': 'gd_channel_typeid_cn',
 'gd_contact_address': 'gd_contact_address',
 'gd_contact_name': 'gd_contact_name',
 'gd_contact_sex': 'gd_contact_sex',
 'gd_contact_sex_cn': 'gd_contact_sex_cn',
 'gd_create_time': 'gd_create_time',
 'gd_order_class': 'gd_order_class',
 'gd_order_class_cn': 'gd_order_class_cn',
 'gd_order_content': 'gd_order_content',
 'gd_order_id': 'gd_order_id',
 'gd_order_index': 'gd_order_index',
 'gd_order_index_cn': 'gd_order_index_cn',
 'gd_order_source': 'gd_order_source',
 'gd_order_source_cn': 'gd_order_source_cn',
 'gd_order_status': 'gd_order_status',
 'gd_order_status_cn': 'gd_order_status_cn',
 'gd_order_type': 'gd_order_type',
 'gd_order_type_cn': 'gd_order_type_cn',
 'gd_service_level1': 'gd_service_level1',
 'gd_service_level1_cn': 'gd_service_level1_cn',
 'gd_service_level2': 'gd_service_level2',
 'gd_service_level2_cn': 'gd_service_level2_cn',
 'gd_service_level3': 'gd_service_level3',
 'gd_service_level3_cn': 'gd_service_level3_cn',
 'gd_service_level4': 'gd_service_level4',
 'gd_service_level4_cn': 'gd_service_level4_cn',
 'gd_session_id': 'gd_session_id',
 'gd_work_no': 'gd_work_no',
 'gd_wx_order_type': 'gd_wx_order_type',
 'gd_wx_order_type_cn': 'gd_wx_order_type_cn',
 'id': 'id',
 'section_id': 'section_id'}
