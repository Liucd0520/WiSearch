
# mysql_uri = 'mysql+mysqlconnector://sh12333_znrpt:Znrpt14!$@10.218.0.3:3324/sh_12333_znrpt'
mysql_uri = 'mysql+mysqlconnector://chatbi:IDEAL@172.31.24.111:3307/shanghai'
param_uri = 'mysql+mysqlconnector://root:liucd123@172.31.24.111:3307/xingchentwo'  # !!


data_table_names = ['shanghai', ]
param_table_metadata = 'field_metadata'  # 't_metadata'
# param_table_search = 't_search'
# param_table_sementic = 't_semantic'
# param_table_abbr = 't_abbr'

# milvus
collection_name = 'collection_shanghai'
uri = 'http://172.31.24.111:19534'

primary_key_name = '工单编号'

is_semantic_analysis = True 
unstructrued_column = '内容描述'
large_step = 200
small_step = 20 
window_size = 100 
min_samples = 5
extend_field = '诉求地址'
limit = 5000 


is_abbr_analysis = False 


# 保存路径
log_dir = './logs'
data_save_dir = './data_shanghai'
bm25_ef_path='data_shanghai/shanghai_bm25.json'

# 枚举值参数
max_distinct_values_num = 100
max_combined_values_length = 1000
# 视图索引 控制不同的查询权限
view_index = ''
# 字符串类型里哪些是有datetime类型的字段
datetime_type_field = []

# 中英文字段对照
columns_map = {'工单编号': 'id',
                "工号": "employee_id",
                "工单生成时间": "order_date",
                '诉求地址': 'address',
                '诉求区域': "region",
                '内容描述': "content_description",
                "工单类别":'order_category',
                "处理描述": 'resolution_description',
                "客户类型": "customer_type",
                "一级分类":"primary_classification",
                '二级分类': "secondary_classification",
                '三级分类': "tertiary_classification",
                '四级分类': "quaternary_classification",
                '主办单位': "responsible_department",
                '是否匿名': "is_anonymous",
                "服务类型": "service_type",
                "通话编号": 'call_id',
                '工单类型': "order_type",
                "新一级分类":"new_primary_classification",
                '新二级分类': "new_secondary_classification",
                '新三级分类': "new_tertiary_classification",
                '新四级分类': "new_quaternary_classification",
                '新五级分类': "new_period_classification",
    }
