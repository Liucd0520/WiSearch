
param_uri = 'mysql+mysqlconnector://root:liucd123@172.31.24.111:3307/xingchentwo'
milvus_uri = 'http://172.31.24.111:19534'


# 保存路径
log_dir_name = 'logs'
data_save_dir = '/data/yfzx/liucd/data'

# 会重新的字段
large_step = 200
small_step = 20 
window_size = 100 
min_samples = 5
limit = 5000 


# 保持不变，如果有缩写分析的列或语义的列，会重新赋值的
is_abbr_analysis = False 
is_semantic_analysis = False 

# 保持不变，如果开启语义分析，会重写的
unstructured_column = ''
extend_field = ''
columns_map = {}
datetime_type_field = ['工单生成时间']


"""没加在数据库里的两个参数"""
# 枚举值参数  
max_distinct_values_num = 100
max_combined_values_length = 1000

# 字符串类型里哪些是有datetime类型的字段
datetime_type_field = []


# 视图索引 控制不同的查询权限
view_index = ''