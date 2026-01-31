import os
import uuid
import sqlite3
from typing import Union, Dict, Any, Optional
from loguru import logger
import chainlit.data as cl_data
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from app.utils import utils

# 设置 SQLite 数据库文件路径
DB_PATH = os.path.join(os.getcwd(), "chainlit.db")

class StorageClient:
    def __init__(self, bucket: str = ""):
        try:
            self.bucket = bucket
            logger.info("StorageClient initialized")
        except Exception as e:
            logger.warning(f"StorageClient initialization error: {e}")

    async def upload_element(self, content: Union[bytes, str], mime: str = 'application/octet-stream') -> Dict[str, Any]:
        try:
            filename = str(uuid.uuid4())
            extname = ".bin" 
            object_key = filename + extname
            file_path = os.path.join(utils.upload_dir(), object_key)
            
            mode = 'wb' if isinstance(content, bytes) else 'w'
            with open(file_path, mode) as f:
                f.write(content)
            
            return {"object_key": object_key, "url": f"/uploads/{object_key}"}
        except Exception as e:
            logger.warning(f"StorageClient upload error: {e}")
            return {}

def get_connection_url():
    # SQLite 的 SQLAlchemy 连接字符串格式
    # 使用 aiosqlite 支持异步
    return f"sqlite+aiosqlite:///{DB_PATH}"

def __init_tables():
    # 针对 SQLite 优化的建表语句
    # 1. UUID/JSONB 改为 TEXT
    # 2. TEXT[] 改为 TEXT
    sql = '''
CREATE TABLE IF NOT EXISTS users (
    "id" TEXT PRIMARY KEY,
    "identifier" TEXT NOT NULL UNIQUE,
    "metadata" TEXT NOT NULL,
    "createdAt" TEXT
);

CREATE TABLE IF NOT EXISTS threads (
    "id" TEXT PRIMARY KEY,
    "createdAt" TEXT,
    "name" TEXT,
    "userId" TEXT,
    "userIdentifier" TEXT,
    "tags" TEXT,
    "metadata" TEXT,
    FOREIGN KEY ("userId") REFERENCES users("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS steps (
    "id" TEXT PRIMARY KEY,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "threadId" TEXT NOT NULL,
    "parentId" TEXT,
    "disableFeedback" BOOLEAN NOT NULL,
    "streaming" BOOLEAN NOT NULL,
    "waitForAnswer" BOOLEAN,
    "isError" BOOLEAN,
    "metadata" TEXT,
    "tags" TEXT,
    "input" TEXT,
    "output" TEXT,
    "createdAt" TEXT,
    "start" TEXT,
    "end" TEXT,
    "generation" TEXT,
    "showInput" TEXT,
    "language" TEXT,
    "indent" INT,
    "defaultOpen" TEXT
);

CREATE TABLE IF NOT EXISTS elements (
    "id" TEXT PRIMARY KEY,
    "threadId" TEXT,
    "type" TEXT,
    "url" TEXT,
    "chainlitKey" TEXT,
    "name" TEXT NOT NULL,
    "display" TEXT,
    "objectKey" TEXT,
    "size" TEXT,
    "page" INT,
    "language" TEXT,
    "forId" TEXT,
    "mime" TEXT,
    "props" TEXT
);

CREATE TABLE IF NOT EXISTS feedbacks (
    "id" TEXT PRIMARY KEY,
    "forId" TEXT NOT NULL,
    "value" INT NOT NULL,
    "comment" TEXT
);
    '''
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(sql) # SQLite 使用 executescript 执行多行语句
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"SQLite tables initialized at {DB_PATH}")

def init():
    # SQLite 不需要 __init_db，直接建表即可（会自动生成文件）
    __init_tables()
    
    # 创建标准的 SQLAlchemy 数据层 (需要安装 aiosqlite)
    layer = SQLAlchemyDataLayer(
        conninfo=get_connection_url(),
        show_logger=False
    )
    
    # 注入自定义存储逻辑
    client = StorageClient()
    layer.upload_element = client.upload_element 
    
    cl_data._data_layer = layer