from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chat_system.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    preferences = Column(JSON, default=dict)

class ChatMessage(Base):
    """聊天消息模型"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    role = Column(String)
    content = Column(Text)
    audio_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserMemory(Base):
    """用户记忆模型"""
    __tablename__ = "user_memories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    memory_type = Column(String)
    content = Column(Text)
    embedding = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
