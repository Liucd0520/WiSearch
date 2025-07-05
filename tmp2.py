import re

def extract_in_values(input_str):
    # 第一步：匹配IN(...)中的括号内容（忽略IN大小写）
    # 正则说明：\bin\b匹配完整单词IN，\s*匹配空格，\(匹配左括号，(.*?)非贪婪捕获括号内内容，\)匹配右括号
    in_pattern = re.compile(r'\bin\b\s*\(\s*(.*?)\s*\)', re.IGNORECASE)
    match = in_pattern.search(input_str)
    if not match:
        return []  # 未找到IN子句，返回空列表
    
    inner_content = match.group(1)  # 获取括号内的原始内容（如：'大数据事业部', '金融数智事业部'）
    
    # 第二步：提取单引号内的所有值（忽略项之间的逗号和空格）
    # 正则说明：'([^']+)'匹配单引号内的非单引号字符，捕获组1为目标值
    value_pattern = re.compile(r"'([^']+)'")
    values = value_pattern.findall(inner_content)  # 提取所有匹配的单引号内字符串
    
    return values

# 测试字符串
input_str = "`DEPT` in ('大数据事业部', '金融数智事业部')"
result = extract_in_values(input_str)
print(result)  # 输出：['大数据事业部', '金融数智事业部']

# 其他测试场景
test_cases = [
    "WHERE dept IN ('a', 'b')",  # 小写in
    "NOT in ( 'hello world' , 'test' )",  # 括号内有空格
    "IN ('a,b', 'c,d')",  # 值包含逗号
    "NO IN HERE",  # 无IN子句
]
for case in test_cases:
    print(extract_in_values(case))
# 输出：
# ['a', 'b']
# ['hello world', 'test']
# ['a,b', 'c,d']
# []