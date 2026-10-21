# scripts/test_friend.py
import sqlite3
import hashlib

def setup_test_data():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    print("开始准备测试数据...")

    # 1. 确保测试用户 B (testB) 存在
    c.execute("SELECT id FROM users WHERE username='testB'")
    r = c.fetchone()
    if not r:
        # 如果没有，则创建，默认密码 123456
        c.execute("INSERT INTO users (username, password_hash, sases_id) VALUES ('testB', ?, 'sases_testB')", (hashlib.sha256(b'123456').hexdigest(),))
        b_id = c.lastrowid
        print(f"✅ 已创建测试用户 testB (用户ID: {b_id})")
    else:
        b_id = r[0]
        print(f"ℹ️ 测试用户 testB 已存在 (用户ID: {b_id})")

    # 2. 确保好友关系存在
    # 注意：这里补上了 friend_agent_id 的 NOT NULL 约束，用 'dummy_agent' 占位
    c.execute("SELECT id FROM agent_friendships WHERE user_id=2 AND target_user_id=?", (b_id,))
    r = c.fetchone()
    if not r:
        c.execute(
            "INSERT INTO agent_friendships (user_id, friend_agent_id, target_user_id, status, friend_mode) VALUES (2, 'dummy_agent', ?, 'accepted', 'normal')", 
            (b_id,)
        )
        friend_id = c.lastrowid
        print(f"✅ 已建立好友关系 (关系记录ID: {friend_id})")
    else:
        friend_id = r[0]
        print(f"ℹ️ 好友关系已存在 (关系记录ID: {friend_id})")

    # 3. 确保好友会话存在
    c.execute("SELECT id FROM conversations WHERE user_id=2 AND is_friend_chat=1")
    r = c.fetchone()
    if not r:
        c.execute("INSERT INTO conversations (user_id, title, is_friend_chat, friend_mode) VALUES (2, '与 testB 聊天', 1, 'normal')")
        conv_id = c.lastrowid
        print(f"✅ 已创建好友专属会话 (会话ID: {conv_id})")
    else:
        conv_id = r[0]
        print(f"ℹ️ 好友会话已存在 (会话ID: {conv_id})")

    conn.commit()
    conn.close()

    print("\n" + "="*50)
    print(f"🎯 准备完毕！请记住你的 CONV_ID = {conv_id}")
    print("接下来测试时，请把 curl 里的 {CONV_ID} 替换为这个数字。")
    print("="*50)

if __name__ == "__main__":
    setup_test_data()
