
# ### Task Description
# Given a query, extract relevant named entity or generate a list of relevant keywords  that are closely related to the query. 
# The output should include important concepts, objects, organization, institution, people, places, or actions mentioned or implied in the query. 
# If the query includes a named entity, extract that named entity
# If the query does not contain  specific named entities but rather some common content, generate a list of keywords
# Ensure that the keywords are diverse and cover different aspects of the query.

# #### Input (Query)
# "近半年有哪些消防火灾事件发生"

# #### Output (Keywords)
# ["消防", "火灾", "爆炸", "气体泄漏", "燃烧", "失火", "煤气泄漏", "储油罐倒塌", "起火", "炸药", "冒火", "着火", "燃气泄漏", "易燃", "易爆", "消防隐患", "灭火器", "消防栓", "消防通道", "纵火", "放火", "烟雾报警器", "浓烟", "火灾报警器"] 


create_event_keyword_prompt = """
### Task Description
Given a query, extract relevant named entity or generate a list of relevant keywords  that are closely related to the query. 
The output should include important concepts, objects, organization, institution, people, places, or actions mentioned or implied in the query. 
If the query includes a named entity, extract that named entity
If the query does not contain  specific named entities but rather some common content, generate a list of keywords
Ensure that the keywords are diverse and cover different aspects of the query.

### Example

#### Input (Query)
"上海近半年有哪些小区存在飞线充电的问题"

#### Output (Keywords)
["小区"] 

### Your Task
Now, given the following query, generate a list of relevant entities or keywords :

#### Input (Query)
{query}

#### Output (Keywords)

"""


create_documentgrade_prompt_template = """
# 指令
你是一个评估器，负责评估检索到的文档内容与用户输入问题之间的相关性。
如果用户的问题与文档表示相同的语义，则判定为相关；如果关键词的含义与文档表示的含义相关度很低，则判断为不相关。目标是过滤掉错误的检索结果。
请输出一个二进制分数 'yes' 或者 'no' 来表示文档是否与用户的问题相关。不要输出任何解释信息。

# 检索到的文档为：
{document}

# 用户输入问题为：
{query}

# 输出二进制分数：

"""


#    "reason": "该事件是由于由于小区的区委书记不作为引起的，所以标签是正确的"
create_clf_prompt_template = """
    # 指令，你是一个AI助手，帮助用户做分类的任务。现在给你一段文本描述，以及一个问题查询，请判断这个问题查询与这段描述是不是匹配的，结果以json的格式返回。如果是则返回"yes"，如果错误则返回"no"
    json的格式进行输出，格式如下:
    {{
        "binary_score": "<返回的结果>"
    }}

    # one-shot example
    ### 查询的问题
    物业不作为事件

    ### 给定的文档
    市民来电反映:上述地址小区垃圾分类目前无人进行，市民表示该问题是由于前小区居委总书记潘丽华不作为导致，该人员目前在彭浦镇其他小区内工作，其不清楚具体工作地址信息，其希望对该人员之前工作进行投诉。诉求：希望管理部门核实处理。（市民要求信息保密，无需回复）
    
    ### 输出：
    {{
        "binary_score": "yes",
    }}

    
    # 查询的问题：
    {query}
    
    # 给定的文档：
    {document}

    # 输出的结果为:
    
    """


create_extract_prompt_template = """
    # 指令：
    你是一个信息抽取器，根据查询的问题对给定的文档进行信息抽取，抽取出能回答问题的具体答案，如果没有相关答案请返回空字符串。
    ## one-shot 
    #### 输入：
    问题：夜间施工的小区有那些？
    文档：市民来电反映:徐汇区浦北路375号康健绿苑在2024年5月8日被围起来了进行改建施工，之前施工时间7:00-18:00，双休也照常，但6月6日开始要进行夜间施工了，有严重挖机噪音扰民，而且端午假期也要到了，故来电反映，诉求：要求停止夜间施工和不要在端午节假日施工。 
    #### 输出：
    {{"extracted_entity": "康健绿苑"}}

    
    现在给你一个问题与文档，抽取所需要的内容，内容要准确精细，不能一概而论，要求结果需要以json的形式输出，不要有其他任何的解释
    
    # 查询的问题：
    {query}
    
    # 给定的文档：
    {document}
    
    # 输出结果为:

"""



obtain_keyword_prompt = """
# 指令
你是一个信息抽取器，对于给定的query，请抽取query中要查询的目标字段，并以json的格式输出
抽取的信息禁止为空

# 例子1
## input:
#### query
半年来偷税漏税的企业有哪些
## output:
{{
"extract_target": "企业"
}}


# 例子2
## input:
#### query
在浦东拼多多投诉最多的商品有什么
## output:
{{
"extract_target": "商品"
}}


# input:
## query：
{query}

# otuput:

"""

obtain_keyword_list_prompt = """
# 指令
你是一个信息抽取器，对于给定的query，请抽取query中要查询的目标字段，并以json的格式输出
抽取的信息禁止为空
如果有多个要抽取的信息，请不要遗漏


## 输出格式

请按照以下json格式提供您的输出结果，不要输出markdown，不要有其他额外的解释信息，通过填充[]中的占位符，请一步步思考。
{{

    "extract_target": [从query里抽取的目标字段]
}}


## 例子1
### input:
#### query
半年来偷税漏税的企业有哪些
### output:
{{
"extract_target": ["企业"]
}}

## 例子2
### input:
#### query
查询案件文书中原告的姓名、性别、出生日期、住址
### output:
{{
"extract_target": ["原告姓名", "原告性别", "原告出生日期", "原告住址"]
}}


# input:
## query：
{query}

# output

"""


create_extraction_prompt_template = """
    # 指令：
    你是一个信息抽取器，需要从给定的字典信息中抽取能够回答查询问题的信息。
    如果没有抽取到信息则输出为""
    
    ## few-shot 
    #### 输入问题：
        问题：夜间施工的小区有那些？
    #### 给定的字典信息：
        {{
            "地址": "虹口区衡水路89弄小区附近"
            "内容描述": "市民来电反映:上述小区附近，每天22:00后会有人修路，不是2、3天，已经修了1个月了，并且越修越响，工人直接将管子砸在地上，凌晨2：00还没停，影响居民休息。诉求：要求马上停止施工并给市民说法。", 
        }}
    #### 输出：
    {{
    "小区": "衡水路89弄小区"
    }}
    
    
    现在给你一个问题与字典信息，抽取所需要的内容，内容要准确精细，不能一概而论，要求结果需要以json的形式输出，不要有其他任何的解释
    
    json的格式进行输出，格式如下:
    {{
        "{key_word}": "<抽取的信息>"
    }}

    # 查询的问题：
    {query}
    
    # 给定的字典信息：
    {document_with_address}

    # 输出结果为:

"""

# 如果没有抽取到信息则输出为""
create_extraction_list_prompt_template = """
    # 指令：
    你是一个信息抽取器，需要从给定的信息中抽取能够回答查询问题的信息，并以json的格式输出
    
    
    现在给你一个问题与字典信息，抽取所需要的内容，内容要准确精细，不能一概而论，要求结果需要以json的形式输出，不要有其他任何的解释
    
    json的格式进行输出，格式如下:
    {key_word_json}

    # 给定的字典信息：：
    {document_with_address}
    

    # 查询的问题：
    {query}
    
    # 输出结果为: 

"""


create_judge_extend_prompt = """
    # 指令
    你是一个判别器，要根据给定的<查询问题>与<回答该问题所对应的信息>，这个信息是从相关信息中抽取出来的，判断抽取的这个信息是否能够部分地回答这个问题，如果不能则返回"no"， 能够回答则返回"yes"，并给出理由，不要输出markdown格式
    注意：<回答该问题所对应的信息>不需要全面满足<查询问题>
    ## two-shot 样例
    #### 输入：
    查询的问题：夜间施工的小区有那些
    对应的回答信息：上述小区
    #### 输出：
    {{
        "binary_score": "no",
        "reason":  "因为只提到上述小区，没有涉及具体的小区名称的相关信息，所以无法回答这个问题"
    }}

    #### 输入：
    查询的问题：具有多媒体教室的中学有哪些
    对应的回答信息： 华东师范大学附属中学东昌南校
    #### 输出
    {{
        "binary_score": "yes",
        "reason":  "华东师范大学附属中学东昌南校是中学之一，所以正确"
    }}

    ## 输入：
    查询的问题：{query}
    对应的回答信息：{extracted_info}
    ## 输出（禁止输出markdown格式）：

"""

    


create_summary_prompt_template = """

## 指令

请你总结市市民众反映的多起同类事件，并用简洁的语言点明市民反映的具体问题。请确保总结不超过20个字，同时避免使用过于宽泛的词汇，>如“管理问题”或“群体事件”等,要能反映出事件中的核心问题。

## one-shot示例
#### 输入的同类事件示例：
[
    市民来电反映:上述地址村委规定，停车费房东收费300元每月，其他的租客要收900元每月。诉求：希望核实收费是否合规。（市民要求信息
保密 需回复）, 
    市民来电反映:其是来外务工人员，居住在上述村，市民表示上述地址村从2月1日开始对于外来人员，收取停车费900元一个月，市民认为该>收费非常不合理，故来电投诉，要求相关部门尽快处理解决。（市民要求信息保密 需回复）, 
    【微信】市民反映：2月1日上述地址曹路镇启明村，进村路口装栏杆闸机，拆绿化带造停车场，本村人不收费，收取外地人停车费（900元/>月），收费标准极不合理（详见附件）。诉求：请管理部门核实合理收取停车费。（市民要求信息保密，需要回复）, 
    市民来电反映:浦东新区曹路镇启明村有停车收费，本地村民不收，房东手里有一张名额，有名额的租客，每个月只需要支付300元，没有名>额的，每个月需要支付900元的停车费，市民认为收费太高，来电诉求：请管理部门核实督促村委降低停车收费标准。（市民要求信息保密 无需回复>）
    市民来电反映:上述地址村委规定，停车费房东收费300元每月，其他的租客要收900元每月。市民认为不合理收费过高。诉求：请管理部门进
行调整收费标准。（需回复）
]

#### 输出的主题示例为（不要超过12个字）：
村里停车场乱收费

    
## 输入同类事件:
{docs_list}

## 输出主题（不要超过20个字）:

"""


query_router_prompt_template = """
    You are an expert at routing a user question to low level extraction (NER task) or high level abstraction (Summary task).
    The NER task means extracting relevant entity information from a given document based on query intent, 
    while the Summary task means generating an information summary of the document based on query intent.

    \n\n User question: {query}

"""

