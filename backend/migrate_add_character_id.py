"""
数据库迁移脚本 - 为chat_messages表添加character_id字段
运行方式: python migrate_add_character_id.py
"""
import sqlite3
import os

# 数据库路径
db_path = os.path.join(os.path.dirname(__file__), "chat_system.db")

def migrate():
    """执行数据库迁移"""
    print(f"正在连接数据库: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(chat_messages)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "character_id" in columns:
            print("✓ character_id 字段已存在，无需迁移")
            return
        
        # 添加character_id字段
        print("正在添加 character_id 字段...")
        cursor.execute("""
            ALTER TABLE chat_messages 
            ADD COLUMN character_id VARCHAR
        """)
        
        # 为已有记录创建索引
        print("正在创建索引...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_messages_character_id 
            ON chat_messages(character_id)
        """)
        
        conn.commit()
        print("✓ 数据库迁移成功！")
        print("  - 已添加 character_id 字段")
        print("  - 已创建索引 idx_chat_messages_character_id")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ 迁移失败: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
