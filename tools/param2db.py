import pandas as pd
import json
# 存入数据库
from sqlalchemy import create_engine

# # 关联检索
# with open('tools/dis_values.json', 'r', encoding='utf-8') as f:
#     data = json.load(f)

# # 缩写 （用事项名称模拟）
# with open('tools/dis_values.json', 'r', encoding='utf-8') as f:
#     data = json.load(f)
#     data = {'事项名称': data['事项名称']}

# # 参数
# data = {'is_semantic_analysis': 1,
#         'large_step': 100,
#         'small_step': 5,
#         'window_size': 20,
#         'min_samples': 5,
#         'extend_field': '上报地址',
#         }
# data = {k:[v] for k, v in data.items()}



# # 参数是不用做如下填充的
# # 找到最大长度
# max_len = max(len(v) for v in data.values())

# # 填充较短的列表
# for key in data:
#     data[key] += [None] * (max_len - len(data[key]))  # 使用 None 填充


# # 转换为 DataFrame
# df = pd.DataFrame(data)


# 元数据
df = pd.read_excel('tools/field_metadata.xlsx', ) 

if __name__ == '__main__':
    # 创建数据库连接
    # 替换为你自己的数据库连接字符串
    mysql_uri = 'mysql+mysqlconnector://root:liucd123@localhost:3306/param' 

    engine = create_engine(mysql_uri)  # 替换为你自己的数据库连接
    df.to_sql('t_metadata', con=engine, if_exists='replace', index=False)
