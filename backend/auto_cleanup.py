# -*- coding: utf-8 -*-
"""
自动清理已删除角色的聊天记录（非交互式）
"""

import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import SessionLocal, ChatMessage
from app.services.character_manager import character_manager


def auto_cleanup():
    """自动清理脏数据"""
    db = SessionLocal()
    
    try:
        valid_character_ids = set(character_manager.characters.keys())
        
        print("=" * 60)
        print("[AUTO CLEANUP] 自动清理数据库脏数据")
        print("=" * 60)
        print(f"\n[INFO] 当前有效角色ID: {valid_character_ids}")
        
        all_messages = db.query(ChatMessage).all()
        print(f"[INFO] 数据库中共有 {len(all_messages)} 条聊天记录")
        
        orphaned_messages = []
        for msg in all_messages:
            if msg.character_id and msg.character_id not in valid_character_ids:
                orphaned_messages.append(msg)
        
        if not orphaned_messages:
            print("\n[OK] 太棒了！没有发现脏数据，数据库很干净！")
            return
        
        print(f"\n[WARNING] 发现 {len(orphaned_messages)} 条属于已删除角色的脏数据：\n")
        
        character_msg_count = {}
        for msg in orphaned_messages:
            char_id = msg.character_id
            if char_id not in character_msg_count:
                character_msg_count[char_id] = 0
            character_msg_count[char_id] += 1
        
        for char_id, count in character_msg_count.items():
            print(f"   - 角色 {char_id}: {count} 条记录 (将删除)")
        
        print("\n[PROCESSING] 正在删除脏数据...")
        
        deleted_count = 0
        for msg in orphaned_messages:
            db.delete(msg)
            deleted_count += 1
            
            if deleted_count % 5 == 0:
                print(f"   已删除 {deleted_count}/{len(orphaned_messages)}...")
        
        db.commit()
        
        print(f"\n[SUCCESS] 清理完成！共删除 {deleted_count} 条脏数据")
        print("\n[TIPS] 后续步骤:")
        print("1. 重启后端服务")
        print("2. 清除浏览器缓存 (Ctrl+Shift+Delete)")
        print("3. 或使用无痕模式测试")
        
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] 清理失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    auto_cleanup()
