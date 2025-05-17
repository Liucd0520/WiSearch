
# mysql_uri = 'mysql+mysqlconnector://root:liucd123@localhost:3306/12345'
mysql_uri = 'mysql+mysqlconnector://root:liucd123@172.31.24.111:3307/12345'
table_names = ['HongKouDemo', ]

# milvus
collection_name = 'hongkou_hotline_order3'
uri = 'http://172.31.24.111:19535'
bm25_ef_path='tools/hongkou_hotline_bm25.json'
limit = 1000


log_dir = './logs'
data_save_dir = './data_hongkou'


related_columns = ['事项大类', '事项小类',  '事项名称', '事项标签', '案件描述/内容描述']
max_distinct_length = 200  # 这个参数对于元数据生成的速度太关键了

# 视图索引 控制不同的查询权限
view_index = '案件编号'

# 语义分析的flag
is_semantic_analysis = True
large_step = 200 
small_step = 20

# dbscan min_samples
min_samples = 5

datetime_type_field = ['发现时间', '收单时间', '派遣时间']
extend_field =  '上报地址'


columns_map = {
    '案件编号': 'Case_ID',
    '原编号': 'Original_ID',
    '案件来源/信息来源': 'Case_Source',
    '工单类型': 'Work_Order_Type',
    '发现时间': 'Discovery_Time',
    '状态': 'Status',
    '事项类别': 'Item_Category',
    '事项大类': 'Major_Item_Category',
    '事项小类': 'Minor_Item_Category',
    '事项名称': 'Item_Name',
    '事项标签': 'Item_Tag',
    '案件描述/内容描述': 'Case_Description',
    '上报地址': 'Reported_Address',
    '实际地址': 'Actual_Address',
    '联系人': 'Contact_Person',
    '联系电话': 'Contact_Number',
    '所属街道': 'Street_Affiliation',
    '主责部门': 'Primary_Department',
    '协同部门': 'Collaborative_Department',
    '主处置部门': 'Primary_Disposal_Department',
    '协同处置部门': 'Collaborative_Disposal_Department',
    '办理描述': 'Handling_Description',
    '结案时间': 'Closure_Time',
    '结案期限(是否超时)': 'Closure_Deadline_Overdue',
    '市紧急程度': 'City_Urgency_Level',
    '收单时间': 'Receiving_Time',
    '紧急程度': 'Urgency_Level',
    '所属片区': 'Area_Affiliation',
    '所属居委': 'Community_Committee_Affiliation',
    '派遣时间': 'Dispatch_Time',
    '案件期限': 'Case_Deadline',
    '处置计时': 'Disposal_Timer',
    '案件整体计时': 'Overall_Case_Timer',
    '事实认定': 'Fact_Recognition',
    '诉求认定': 'Request_Recognition',
    '是否解决区回访': 'Is_Zone_Follow_Up_Solved',
    '是否满意区回访': 'Is_Zone_Follow_Up_Satisfied'
}
