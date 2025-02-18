#模型下载
from modelscope import snapshot_download
model_dir = snapshot_download('yangjhchs/acge_text_embedding')
model_dir = snapshot_download('BAAI/bge-reranker-v2-m3')