#!/usr/bin/env python3
import os
from GetAnswer import (
    analyze_query,
    get_knowledge_based_answer,
    query_uuid,
    analyze_sql_results2,
    extract_format_content
)
from Config import *  # 导入相关配置，如 DEEPSEEK_API、RERANK_MODEL_PATH 等

def main():
    # 设置测试用例，此处以 "再生铝" 为例；可根据需要切换其他测试用例
    query_dict = {'activity_name': None, 'geography': None, 'reference_product_unit': None}

    query_dict = {"activity_name": "再生铝", "geography": "乌克兰", "reference_product_unit": "kg"}

    query_dict = {"activity_name": "丁苯胶", "geography": "", "reference_product_unit": ""}

    query_dict = {"activity_name": "烧碱", "geography": "欧洲", "reference_product_unit": ""}

    query_dict = {"activity_name": "醋酸乙酯", "geography": "", "reference_product_unit": ""}

    # query_dict = {"activity_name": "氢氧化钠", "geography": "", "reference_product_unit": ""}

    # query_dict = {"activity_name": "45号钢", "geography": "", "reference_product_unit": "kg"}

    # query_dict = {"activity_name": "十溴二苯醚", "geography": "", "reference_product_unit": "t"}

    # query_dict = {"activity_name": "二甲苯", "geography": "", "reference_product_unit": "kg"}

    #query_dict = {"activity_name": "促进剂", "geography": "", "reference_product_unit": ""}

    #query_dict = {"activity_name": "西南电网", "geography": "", "reference_product_unit": ""}
    # 获取近义词列表，并将原始活动名称作为首项
    query_list = analyze_query(query_dict)
    query_list.insert(0, query_dict['activity_name'])
    print("query_list的内容:", query_list)

    query_str = str(query_dict)
    print("当前的query:", query_str)

    # 构造向量数据库路径（基于 main.py 的位置）
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    vector_db_path = os.path.join(BASE_DIR, "../data/faiss_all_acge")

    # 调用向量检索与 rerank，获得知识库返回的文本
    uuid_result = get_knowledge_based_answer(
        vector_db_path=vector_db_path,
        queries=query_list,
        top_k_embedding_docs=100,
        top_k_rerank_docs=5
    )
    print("uuid_result:", uuid_result)

    # 从返回文本中提取 UUID，并在数据库中查询对应记录
    sql_results = query_uuid(uuid_str=uuid_result, table_name='environmental_data')
    print("sql_results:", sql_results)

    # 调用 LLM 分析 SQL 结果，过滤排序后提取格式化部分
    final_result = extract_format_content(analyze_sql_results2(query_str, sql_results))
    print("最终结果:", final_result)

if __name__ == '__main__':
    main()
