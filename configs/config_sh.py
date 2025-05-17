
# mysql_uri = 'mysql+mysqlconnector://root:liucd123@localhost:3306/12345'
mysql_uri = 'mysql+mysqlconnector://root:liucd123@172.31.24.111:3307/12345'
table_names = ['shanghai', ]

# milvus
collection_name = 'collection_shanghai'
uri = 'http://172.31.24.111:19535'
bm25_ef_path='tools/shanghai_bm25.json'
primary_key_name = '工单编号'

limit = 1000

# 保存路径
log_dir = './logs'
data_save_dir = './data_shanghai'

# 
related_columns = ['一级分类', '二级分类',  '三级分类', '四级分类', '内容描述']
max_distinct_length = 200  # 这个参数对于元数据生成的速度太关键了

# 视图索引 控制不同的查询权限
view_index = '工号'


# 语义分析的flag
is_semantic_analysis = True
large_step = 200 
small_step = 20

# dbscan min_samples
min_samples = 5

datetime_type_field = ['发现时间', '收单时间', '派遣时间']
extend_field =  '诉求地址'


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
