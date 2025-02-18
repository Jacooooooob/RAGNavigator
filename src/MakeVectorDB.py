from langchain_community.document_loaders import CSVLoader
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS


from Embedding import embeddings
from datetime import datetime
import shutil

def load_file(filepath: str):
    # 获取当前脚本所在目录（src），然后回退上一级进入 data 文件夹
    base_dir = os.path.dirname(__file__)
    abs_filepath = os.path.join(base_dir, "../data", filepath)
    
    # 可选：打印调试信息，确认加载文件的绝对路径
    # print("加载文件路径：", os.path.abspath(abs_filepath))
    
    loader = CSVLoader(file_path=abs_filepath, encoding='gbk')
    
    textsplitter = RecursiveCharacterTextSplitter(
        chunk_size=1024,
        chunk_overlap=100,
        length_function=len,
        is_separator_regex=False
    )
    docs = loader.load_and_split(text_splitter=textsplitter)
    return docs




def init_knowledge_vector_db(init_file_path: str, save_path: str = None, overwrite: bool = False):
    if save_path is None:
        current_time = datetime.now().strftime('%Y%m%d%H%M%S')
        save_path = f'../data/faiss_{current_time}'

    save_path = os.path.abspath(save_path)  # 确保路径正确

    try:
        # 如果目录已存在，且 overwrite=True，则删除后重建
        if os.path.exists(save_path):
            if overwrite:
                shutil.rmtree(save_path)  # 删除已有目录
                print(f"覆盖已存在的路径: {save_path}")
            else:
                raise FileExistsError(f"保存路径 {save_path} 已经存在")

        os.makedirs(os.path.join(save_path, 'files'))  # 创建目录

        shutil.copy(init_file_path, os.path.join(save_path, 'files'))
    except Exception as e:
        print(f"初始化时发生错误: {e}")
        return None

    try:
        docs = load_file(init_file_path)
        vector_db = FAISS.from_documents(docs, embeddings)
        vector_db.save_local(save_path)
        return vector_db
    except Exception as e:
        print(f"创建 FAISS 数据库失败: {e}")
        return None



def add_to_knowledge_vector_db(vector_db_path: str, file_path: str):
    try:
        # 检查文件是否已经存在于 files 文件夹中
        files_folder = os.path.join(vector_db_path, 'files')
        target_file_path = os.path.join(files_folder, os.path.basename(file_path))
        if os.path.exists(target_file_path):
            raise FileExistsError(f"文件 {file_path} 已经存在于 {files_folder} 中")

        # 加载文件并添加到知识向量数据库
        docs = load_file(file_path)
        vector_db = FAISS.load_local(folder_path=vector_db_path, embeddings=embeddings,
                                     allow_dangerous_deserialization=True)
        vector_db.add_documents(docs)
        vector_db.save_local(vector_db_path) # 保存 vector_db
        shutil.copy(file_path, target_file_path) # 将文件复制到 files 文件夹中

    except FileExistsError as fee:
        print(fee)
    except Exception as e:
        print(f"处理文件 {file_path} 时发生错误: {e}")

def delete_file_from_knowledge_vector_db(vector_db_path: str, file_path: str):
    try:
        # 获取文件名
        file_name = os.path.basename(file_path)

        # 检查文件是否存在于 files 文件夹中
        files_folder = os.path.join(vector_db_path, 'files')
        target_file_path = os.path.join(files_folder, file_name)
        if not os.path.exists(target_file_path):
            raise FileNotFoundError(f"文件 {file_name} 未存在于 {files_folder} 中")

        # 加载 vector_db
        vector_db = FAISS.load_local(folder_path=vector_db_path, embeddings=embeddings,
                                     allow_dangerous_deserialization=True)
        docstore_dict = vector_db.docstore._dict

        try:
            # 查找需要删除的文件对应的hash值
            delete_hash_id = None
            for hash_key, document in docstore_dict.items():
                if os.path.basename(document.metadata['source']) == file_name:
                    delete_hash_id = hash_key
                    break

            if delete_hash_id is None:
                raise ValueError(f"文件 {file_name} 不存在于 vector_db 中")

            delete_content = docstore_dict[delete_hash_id].page_content
            vector_db.delete([delete_hash_id])

            # 保存更新后的 vector_db
            vector_db.save_local(vector_db_path)

            # 从 files 文件夹中删除文件
            os.remove(target_file_path)
            print(f"成功删除{file_name}的文档，其id为{delete_hash_id} ，具体内容为 {delete_content}")

        except ValueError as ve:
            print(ve)

    except FileNotFoundError as fnfe:
        print(fnfe)
    except Exception as e:
        print(f"处理文件 {file_path} 时发生错误: {e}")


if __name__ == '__main__':
    base_dir = os.path.dirname(__file__)
    init_file_path = os.path.join(base_dir, "../data", "input.csv")
    save_path = os.path.join(base_dir, "../data", "faiss_all_acge")

    vector_db = init_knowledge_vector_db(init_file_path=init_file_path, save_path=save_path, overwrite=True)
    if vector_db:
        print("成功初始化知识向量数据库")
    else:
        print("初始化失败")
