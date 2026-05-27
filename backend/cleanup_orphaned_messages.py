# -*- coding: utf-8 -*-
"""
清理已删除角色的聊天记录（脏数据）
使用方法：
1. 停止后端服务
2. 运行此脚本：python cleanup_orphaned_messages.py
3. 重新启动服务
"""

import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import SessionLocal, ChatMessage
from app.services.character_manager import character_manager


def cleanup_orphaned_messages():
    """清理已删除角色的聊天记录"""
    db = SessionLocal()
    
    try:
        valid_character_ids = set(character_manager.characters.keys())
        
        print(f"[INFO] 当前有效角色ID: {valid_character_ids}")
        print("-" * 60)
        
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
            print(f"   - 角色 {char_id}: {count} 条记录")
        
        confirm = input("\n确定要删除这些脏数据吗？(y/n): ")
        if confirm.lower() != 'y':
            print("[CANCEL] 已取消操作")
            return
        
        for msg in orphaned_messages:
            db.delete(msg)
        
        db.commit()
        
        print(f"\n[SUCCESS] 成功清理 {len(orphaned_messages)} 条脏数据！")
        print("\n[TIPS] 提示：")
        print("1. 请重启后端服务使更改生效")
        print("2. 请清除浏览器缓存（Ctrl+Shift+Delete）或使用无痕模式测试")
        
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] 清理失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def show_database_stats():
    """显示数据库统计信息"""
    db = SessionLocal()
    
    try:
        total = db.query(ChatMessage).count()
        
        character_stats = {}
        messages = db.query(ChatMessage.character_id).distinct().all()
        for (char_id,) in messages:
            if char_id:
                count = db.query(ChatMessage).filter(ChatMessage.character_id == char_id).count()
                character_stats[char_id] = count
        
        print("=" * 60)
        print("[STATS] 数据库统计信息")
        print("=" * 60)
        print(f"总消息数: {total}")
        print("\n按角色分布:")
        for char_id, count in sorted(character_stats.items(), key=lambda x: -x[1]):
            exists = "[VALID]" if char_id in character_manager.characters else "[DELETED]"
            print(f"  - {char_id}: {count}条 ({exists})")
            
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("[TOOL] AI聊天系统 - 数据库清理工具")
    print("=" * 60 + "\n")
    
    while True:
        print("请选择操作:")
        print("1. 查看数据库统计信息")
        print("2. 清理已删除角色的脏数据")
        print("3. 退出")
        
        choice = input("\n请输入选项 (1/2/3): ").strip()
        
        if choice == '1':
            show_database_stats()
            print()
        elif choice == '2':
            cleanup_orphaned_messages()
            print()
        elif choice == '3':
            print("[BYE] 再见！")
            break
        else:
            print("[ERROR] 无效选项，请重新输入\n")
