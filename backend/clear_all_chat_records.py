"""
清空所有聊天记录的脚本
用于清理旧的没有character_id的聊天记录
运行方式: python clear_all_chat_records.py
"""
import sqlite3
import os

# 数据库路径
db_path = os.path.join(os.path.dirname(__file__), "chat_system.db")

def clear_all_chat_records():
    """清空所有聊天记录"""
    print(f"正在连接数据库: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 查询当前有多少条记录
        cursor.execute("SELECT COUNT(*) FROM chat_messages")
        count_before = cursor.fetchone()[0]
        print(f"当前聊天记录数量: {count_before} 条")
        
        if count_before == 0:
            print("✓ 数据库中没有聊天记录")
            return
        
        # 确认清空
        confirm = input(f"⚠️  确定要清空所有 {count_before} 条聊天记录吗？(yes/no): ")
        if confirm.lower() != 'yes' and confirm.lower() != 'y':
            print("已取消操作")
            return
        
        # 清空所有记录
        print("正在清空所有聊天记录...")
        cursor.execute("DELETE FROM chat_messages")
        deleted_count = cursor.rowcount
        
        conn.commit()
        print(f"✓ 成功清空 {deleted_count} 条聊天记录")
        
        # 验证
        cursor.execute("SELECT COUNT(*) FROM chat_messages")
        count_after = cursor.fetchone()[0]
        print(f"当前聊天记录数量: {count_after} 条")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ 清空失败: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    clear_all_chat_records()
