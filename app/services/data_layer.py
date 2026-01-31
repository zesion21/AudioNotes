import os
import uuid
from typing import Union, Dict, Any, Optional # 补充导入 Optional
from loguru import logger
import chainlit.data as cl_data
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.data import BaseDataLayer # 导入新的基类
import psycopg2
from psycopg2 import sql

from app.utils import utils

db_name = os.getenv("POSTGRES_DB", "audio_notes")
db_user = os.getenv("POSTGRES_USER", "postgres")
db_password = os.getenv("POSTGRES_PASSWORD", "admin")
db_host = os.getenv("POSTGRES_HOST", "192.168.125.100")
db_port = os.getenv("POSTGRES_PORT", "65432")

class StorageClient:
    def __init__(self, bucket: str = ""):
        try:
            self.bucket = bucket
            logger.info("StorageClient initialized")
        except Exception as e:
            logger.warning(f"StorageClient initialization error: {e}")

    # 新版 API 使用 upload_element 替代了 upload_file
    # async def upload_element(self, content: Union[bytes, str], mime: str = 'application/octet-stream') -> Dict[str, Any]:
    #     try:
    #         filename = str(uuid.uuid4())
    #         # 获取后缀，如果没有后缀默认用 bin
    #         extname = ".bin" 
    #         # 注意：新版 content 通常直接传入，不再通过 object_key
    #         object_key = filename + extname
    #         file_path = os.path.join(utils.upload_dir(), object_key)
            
    #         mode = 'wb' if isinstance(content, bytes) else 'w'
    #         with open(file_path, mode) as f:
    #             f.write(content)
            
    #         # 返回新版要求的格式
    #         return {"object_key": object_key, "url": f"/uploads/{object_key}"}
    #     except Exception as e:
    #         logger.warning(f"StorageClient, upload_element error: {e}")
    #         return {}

    async def upload_element(self, content: Union[bytes, str], mime: str = 'application/octet-stream') -> Dict[str, Any]:
        try:
            filename = str(uuid.uuid4())
            extname = ".bin" # 或者根据 mime 类型判断后缀
            object_key = filename + extname
            file_path = os.path.join(utils.upload_dir(), object_key)
            
            mode = 'wb' if isinstance(content, bytes) else 'w'
            with open(file_path, mode) as f:
                f.write(content)
            
            return {"object_key": object_key, "url": f"/uploads/{object_key}"}
        except Exception as e:
            logger.warning(f"StorageClient upload error: {e}")
            return {}
# class StorageClient(cl_data.BaseStorageClient):
#     def __init__(self, bucket: str = ""):
#         try:
#             self.bucket = bucket
#             logger.info("StorageClient initialized")
#         except Exception as e:
#             logger.warning(f"StorageClient initialization error: {e}")

#     async def upload_file(self, object_key: str, data: Union[bytes, str], mime: str = 'application/octet-stream',
#                           overwrite: bool = True) -> Dict[str, Any]:
#         try:
#             filename = str(uuid.uuid4())
#             extname = os.path.splitext(object_key)[1].lower()
#             object_key = filename + extname
#             file_path = os.path.join(utils.upload_dir(), object_key)
#             with open(file_path, 'wb') as f:
#                 f.write(data)
#             return {"object_key": object_key, "url": f"/uploads/{object_key}"}
#         except Exception as e:
#             logger.warning(f"StorageClient, upload_file error: {e}")
#             return {}


def get_connection_url(driver: str = "asyncpg"):
    return f"postgresql+{driver}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


# 如果数据库不存在，会自动创建
def __init_db():
    conn = psycopg2.connect(dbname='postgres', user=db_user, password=db_password, host=db_host, port=db_port)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    if not exists:
        conn = psycopg2.connect(dbname='postgres', user=db_user, password=db_password, host=db_host, port=db_port)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
        cur.close()
        conn.close()


def __init_tables():
    sql = '''
CREATE TABLE IF NOT EXISTS users (
    "id" UUID PRIMARY KEY,
    "identifier" TEXT NOT NULL UNIQUE,
    "metadata" JSONB NOT NULL,
    "createdAt" TEXT
);

CREATE TABLE IF NOT EXISTS threads (
    "id" UUID PRIMARY KEY,
    "createdAt" TEXT,
    "name" TEXT,
    "userId" UUID,
    "userIdentifier" TEXT,
    "tags" TEXT[],
    "metadata" JSONB,
    FOREIGN KEY ("userId") REFERENCES users("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS steps (
    "id" UUID PRIMARY KEY,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "threadId" UUID NOT NULL,
    "parentId" UUID,
    "disableFeedback" BOOLEAN NOT NULL,
    "streaming" BOOLEAN NOT NULL,
    "waitForAnswer" BOOLEAN,
    "isError" BOOLEAN,
    "metadata" JSONB,
    "tags" TEXT[],
    "input" TEXT,
    "output" TEXT,
    "createdAt" TEXT,
    "start" TEXT,
    "end" TEXT,
    "generation" JSONB,
    "showInput" TEXT,
    "language" TEXT,
    "indent" INT
);

CREATE TABLE IF NOT EXISTS elements (
    "id" UUID PRIMARY KEY,
    "threadId" UUID,
    "type" TEXT,
    "url" TEXT,
    "chainlitKey" TEXT,
    "name" TEXT NOT NULL,
    "display" TEXT,
    "objectKey" TEXT,
    "size" TEXT,
    "page" INT,
    "language" TEXT,
    "forId" UUID,
    "mime" TEXT
);

CREATE TABLE IF NOT EXISTS feedbacks (
    "id" UUID PRIMARY KEY,
    "forId" UUID NOT NULL,
    "value" INT NOT NULL,
    "comment" TEXT
);
    '''
    conn = psycopg2.connect(dbname=db_name, user=db_user, password=db_password, host=db_host, port=db_port)
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()


# def init():
#     __init_db()
#     __init_tables()
#     cl_data._data_layer = SQLAlchemyDataLayer(conninfo=get_connection_url(),
#                                               storage_provider=StorageClient(),
#                                               show_logger=False)

def init():
    __init_db()
    __init_tables()
    
    # 1. 先创建标准的 SQLAlchemy 数据层
    layer = SQLAlchemyDataLayer(
        conninfo=get_connection_url(),
        show_logger=False
    )
    
    # 2. 重点：手动把你自定义的存储逻辑“嫁接”上去
    client = StorageClient()
    layer.upload_element = client.upload_element 
    
    # 3. 赋值给 Chainlit 内部变量
    cl_data._data_layer = layer