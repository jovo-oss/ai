"""
数据库迁移脚本 - 为 CharacterMemory 添加新字段
"""
import sqlite3
from datetime import datetime
import os

# 数据库文件路径
db_path = os.path.join(os.path.dirname(__file__), 'chat_system.db')

def migrate():
    print(f"正在连接数据库: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查是否已存在 access_count 列
        cursor.execute("PRAGMA table_info(character_memories)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'access_count' not in columns:
            print("正在添加 access_count 列...")
            cursor.execute("ALTER TABLE character_memories ADD COLUMN access_count INTEGER DEFAULT 0")
        
        if 'last_accessed' not in columns:
            print("正在添加 last_accessed 列...")
            cursor.execute("ALTER TABLE character_memories ADD COLUMN last_accessed DATETIME")
            
            # 为现有记录设置默认值
            now = datetime.utcnow().isoformat()
            cursor.execute("UPDATE character_memories SET last_accessed = ? WHERE last_accessed IS NULL", (now,))
        
        conn.commit()
        print("迁移成功完成！")
        
    except Exception as e:
        print(f"迁移出错: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
