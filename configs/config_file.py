
# mysql_uri = 'mysql+mysqlconnector://root:liucd123@localhost:3306/12345'
mysql_uri = 'mysql+mysqlconnector://root:liucd123@172.31.24.111:3307/gjw'
table_names = ['gjw', ]

# milvus
collection_name = 'collection_gjw'
uri = 'http://172.31.24.111:19535'
bm25_ef_path='tools/gjw_bm25.json'
primary_key_name = '编号'

limit = 500

# 保存路径
log_dir = './logs'
data_save_dir = './data_gjw'


related_columns = ['区局', '工种或工作头衔',  '领域', '行业', '工匠介绍']
max_distinct_length = 2000  # 这个参数对于元数据生成的速度太关键了
is_abbr_analysis = True 
abbr_field = '工作单位'

# 视图索引 控制不同的查询权限
view_index = ''


# 语义分析的flag
is_semantic_analysis = True
large_step = 100
small_step = 5
window_size = 20

# dbscan min_samples
min_samples = 5

datetime_type_field = []
extend_field =  '行业'


columns_map = {
  "编号": "Number",
  "年份": "Year",
  "区局": "District",
  "姓名": "Name",
  "年龄": "Age",
  "姓名拼音": "Pinyin_of_Name",
  "性别": "Gender",
  "工作单位": "Workplace",
  "工种或工作头衔": "Title",
  "领域": "Field",
  "行业": "Industry",
  "工匠介绍": "Introduction"
}