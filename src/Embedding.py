# from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.embeddings import ModelScopeEmbeddings
from langchain_community.embeddings import DashScopeEmbeddings
import sentence_transformers

# 可以调用本地的开源的embedding模型
embedding_model_dict = {
    "bge-large-zh":r"D:\Code\models\bge-large-zh",
    "acge-embedding":r"C:\Users\86133\.cache\modelscope\hub\yangjhchs\acge_text_embedding",
    "gte-large-zh":r"D:\Code\models\gte-large-zh",
}

EMBEDDING_MODEL = "acge-embedding"
#初始化 hugginFace 的 embeddings 对象
embeddings = HuggingFaceEmbeddings(model_name=embedding_model_dict[EMBEDDING_MODEL], multi_process=False)
#embeddings.client = sentence_transformers.SentenceTransformer(embeddings.model_name, device='cuda')

# 调用api也可以
# embeddings = DashScopeEmbeddings(
#    model="text-embedding-v2", dashscope_api_key='sk-fb887bcee2c34ac899f1f23ff510a7a9'
# )