from webui_models.webui_llm import *
from module.main_llm import *
from models.langchain_models import llm_qwen_14B, llm_qwen_7B

# 模型
task_aware_chain = task_aware_model(llm_qwen_14B)
schema_linking_chain = schema_linking_model(llm_qwen_14B)
sql_gen_chain = sql_gen_model(llm_qwen_14B)
ner_clf_chain = ner_clf_model(llm_qwen_14B)
sql_feedback_chain = sql_feedback_model(llm_qwen_14B)
text2datetime_chain = datetime_interval_model(llm_qwen_14B)
meta_data_chain = meta_data_model(llm_qwen_14B)
each_meta_data_chain  = each_meta_data_model(llm_qwen_14B)
translate_chain = translate_english_model(llm_qwen_14B)
table_chain = table_linking_model(llm_qwen_14B)

# 配置前端的模型
explanation_chain = query_insight_model(llm_qwen_14B)
chat_chain =  result_chat_model(llm_qwen_14B)
recommand_chain = query_recommand_model(llm_qwen_14B)
