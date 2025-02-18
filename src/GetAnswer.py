from langchain_community.vectorstores import FAISS
from typing import List
from Embedding import embeddings
from Config import *
import psycopg2
import re
from FlagEmbedding import FlagReranker
import time
from langchain_openai import ChatOpenAI
from FlagEmbedding import FlagLLMReranker

llm = ChatOpenAI(
    model='deepseek-chat',
    openai_api_key=DEEPSEEK_API,
    openai_api_base='https://api.deepseek.com',
    max_tokens=4096,
)


def convert_str_to_list(input_str):
    input_str = input_str.strip('[]')  # 去掉字符串两端的方括号
    result_list = input_str.split(',')  # 按逗号分割字符串
    result_list = [item.strip() for item in result_list]  # 去掉每个元素的多余空格
    return result_list


def analyze_query(query: dict):
    prompt = f'''你是一个擅长分析近义词的汉语学家。
    你需要分析<{query['activity_name']}>相关的近义词有哪些,返回前3个最接近的近义词.
    注意:你需要保证输出格式如下,多个词之间用逗号','分开：
    [在这里输入你认为的近义词1,在这里输入你认为的近义词2,在这里输入你认为的近义词3]'''
    result = llm.invoke(prompt).content
    return convert_str_to_list(result)


def get_knowledge_based_answer(vector_db_path: str, queries: list, top_k_embedding_docs: int, top_k_rerank_docs: int):
    top_rerank_knowledge_content = ""  # 用于拼接所有query的结果

    # embedding查找计时
    vector_db = FAISS.load_local(folder_path=vector_db_path, embeddings=embeddings,
                                 allow_dangerous_deserialization=True)

    #reranker = FlagReranker(RERANK_MODEL_PATH, use_fp16=True)  # rerank模型加载

    reranker = FlagLLMReranker(RERANK_MODEL_PATH, use_fp16=True)
    for query in queries:
        # 每个query的embedding查找
        start_time = time.time()
        result = vector_db.similarity_search_with_score(query=query, k=top_k_embedding_docs)
        end_time = time.time()
        # print(f"embedding查找耗时: {end_time - start_time} seconds")

        # 计算 rerank 分数
        start_time = time.time()
        rerank_scores = []
        for doc, _ in result:
            score1 = reranker.compute_score([query, doc.page_content])
            rerank_scores.append((doc, score1))
        end_time = time.time()
        # print(f"rerank分数计算耗时: {end_time - start_time} seconds")

        # 按照 rerank_score 降序排序并取前几个内容拼接 page_content
        start_time = time.time()
        sorted_rerank_scores = sorted(rerank_scores, key=lambda x: x[1], reverse=True)
        for doc, score in sorted_rerank_scores[:top_k_rerank_docs]:
            page_content = doc.page_content.replace('\r\n', '\n').replace('\r', '\n')
            top_rerank_knowledge_content += page_content + "\n\n"  # 使用两个换行符分隔每个page_content

        end_time = time.time()
        # print(f"拼接 top_rerank_knowledge_content 耗时: {end_time - start_time} seconds")

    print(
        f'type(top_rerank_knowledge_content): {type(top_rerank_knowledge_content)},\n top_rerank_knowledge_content:\n {top_rerank_knowledge_content}'
    )

    return top_rerank_knowledge_content


def query_uuid(uuid_str: str, table_name: str):
    # 使用正则表达式提取所有的uuid
    uuids = re.findall(r'activity_uuid_product_uuid: ([a-f0-9\-]+_[a-f0-9\-]+)', uuid_str)
    uuids = list(set(uuids))
    print(type(uuids), len(uuids), uuids)

    if not uuids:
        # print("没有找到uuid")
        return None

    # 连接到数据库
    conn_params = {
        'dbname': 'postgres',
        'user': 'postgres',
        'password': '013777',
        'host': 'localhost',
        'port': '5432'
    }

    # 开始计时
    start_time = time.time()

    # 连接数据库并执行查询
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()

    # 构造SQL查询语句
    query = f"SELECT activity_name, geography, reference_product_unit FROM {table_name} WHERE activity_uuid_product_uuid IN %s"

    # 执行查询
    cursor.execute(query, (tuple(uuids),))
    results = cursor.fetchall()

    # 关闭游标和连接
    cursor.close()
    conn.close()

    # 结束计时
    end_time = time.time()
    elapsed_time = end_time - start_time
    # print(f"执行sql用时 {elapsed_time:.2f} seconds.")

    # 将结果转为字典列表
    keys = ['activity_name', 'geography', 'reference_product_unit']
    dict_results = [dict(zip(keys, row)) for row in results]

    return dict_results


def analyze_sql_results1(query: str, sql_results: List):
    start_time = time.time()
    prompt = f'''你是一个分析师，你需要将【已知】中的多条数据按照和【目标】的相关性进行分析，最后对【已知】的内容进行排序。

    排序需要参考三方面因素：活动名(activity_name),单位(reference_product_unit),地理(geography):
    具体的步骤如下：
    1.首先，将与目标活动名(activity_name)最相关的选项排在最前面。
    2.然后，在活动名相同的情况下，考虑单位(reference_product_unit)相关性。
    3.最后，在活动名和单位相同的情况下，考虑地理(geography)相关性。

    【目标】
    {query}

    【已知】
    {sql_results}

    注意，你需要保证返回的格式如下，格式的要求在xml标签<format>里面。
    <format>
    1.<在这里输入你认为第1适合的答案>;
    2.<在这里输入你认为第2适合的答案>;
    ……
    n.<在这里输入你认为第n适合的答案>;
    </format>
    '''
    print(f'提示词:{prompt}')
    # stream = llm.stream(prompt)
    #
    # return stream
    result = llm.invoke(prompt)
    end_time = time.time()
    elapsed_time = end_time - start_time
    # print(f'elapsed_tim1e', elapsed_time)
    return result.content


def analyze_sql_results2(query: str, sql_results: List):
    start_time = time.time()
    prompt = f'''你是一个分析师，你需要将【已知】中的多条数据按照和【目标】的相关性进行分析，然后过滤掉不符合要求的内容，最后对【已知】的内容进行排序。
    过滤需要考虑两方面因素：活动名(activity_name),单位(reference_product_unit):
    具体的步骤如下：
    1.首先，考虑与目标活动名(activity_name)的相关性。如果是【已知】中的活动名和【目标】的活动名不相关，就直接舍弃。
    2.然后，在活动名符合要求的情况下，考虑单位(reference_product_unit)相关性。如果是【已知】中的单位和【目标】的单位不是同一个量纲，就直接舍弃。

    排序需要参考三方面因素：活动名(activity_name),单位(reference_product_unit),地理(geography):
    具体的步骤如下：
    1.首先，将与目标活动名(activity_name)最相关的选项排在最前面。
    2.然后，在活动名相同的情况下，考虑单位(reference_product_unit)相关性。
    3.最后，在活动名和单位相同的情况下，考虑地理(geography)相关性。

    【目标】
    {query}

    【已知】
    {sql_results}

    注意，你需要保证返回的格式如下，格式的要求在xml标签<format>里面。
    <format>
    1.<在这里输入你认为第1适合的答案>;
    2.<在这里输入你认为第2适合的答案>;
    ……
    n.<在这里输入你认为第n适合的答案>;
    </format>
    '''
    print(f'提示词:{prompt}')
    # stream = llm.stream(prompt)
    #
    # return stream
    result = llm.invoke(prompt)
    end_time = time.time()
    elapsed_time = end_time - start_time
    # print(f'elapsed_tim2e', elapsed_time)
    return result.content


def extract_format_content(xml_str: str):
    # 使用正则表达式提取<format>和</format>标签之间的内容
    match = re.search(r'<format>(.*?)</format>', xml_str, re.DOTALL)

    # 如果没有找到匹配或者内容为空，抛出异常
    if not match or not match.group(1).strip():
        return "没有找到 <format> 和 </format> 之间的内容"
    # 返回提取到的内容
    return match.group(1).strip()