from langgraph.graph import END, StateGraph, START
from operator_workflow.graph import GraphState
from operator_workflow.node import  retrieve, relevance_grade, ENR_with_extension, documents_cluster_summary, documents_simorder
import copy 


workflow = StateGraph(GraphState)

# define nodes

workflow.add_node('retrieve', retrieve)
workflow.add_node('relevance_grade', relevance_grade)
workflow.add_node('NER', ENR_with_extension)
workflow.add_node('documents_cluster_summary', documents_cluster_summary)
workflow.add_node('documents_simorder', documents_simorder)


# Build retrieve graph
workflow_retrieve = copy.deepcopy(workflow)
workflow_retrieve.add_edge(START, 'retrieve')
workflow_retrieve.add_edge('retrieve', 'relevance_grade')


# Build retrieve + extraction graph
workflow_retrieve_extraction = copy.deepcopy(workflow_retrieve)
workflow_retrieve_extraction.add_edge('relevance_grade', 'NER')
workflow_retrieve_extraction.add_edge('NER', END)

# Build retrieve + summary graph
workflow_retrieve_summary = copy.deepcopy(workflow_retrieve)
workflow_retrieve_summary.add_edge('relevance_grade', 'documents_cluster_summary')
workflow_retrieve_summary.add_edge('documents_cluster_summary', END)

# Build retrieve + simoder graph
workflow_simorder = copy.deepcopy(workflow)
workflow_simorder.add_edge(START,  'documents_simorder')
workflow_simorder.add_edge('documents_simorder', END)


# Compile
app_retrieve = workflow_retrieve.compile()
app_retrieve_extraction = workflow_retrieve_extraction.compile()
app_retrieve_summary = workflow_retrieve_summary.compile()
app_simorder = workflow_simorder.compile() 


