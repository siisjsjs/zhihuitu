import sqlite3, os, sys

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def hash_pw(p): return pwd_context.hash(p)
except Exception as e:
    print(f"passlib error: {e}")
    try:
        import bcrypt
        def hash_pw(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
    except Exception as e2:
        print(f"bcrypt error: {e2}")
        sys.exit(1)

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zhihuitu.db")
print(f"DB path: {db_path}")
print(f"DB exists: {os.path.exists(db_path)}")

username = os.environ.get("ADMIN_USERNAME", "admin")
password = os.environ.get("ADMIN_PASSWORD")
if not password:
    print("请先设置环境变量 ADMIN_PASSWORD，例如：set ADMIN_PASSWORD=YourStrongPassword")
    sys.exit(1)

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print("Tables:", cur.fetchall())

    cur.execute("SELECT id FROM users WHERE username=?", (username,))
    if cur.fetchone():
        cur.execute("UPDATE users SET role='admin', is_active=1, hashed_password=? WHERE username=?",
                    (hash_pw(password), username))
        print(f"已将 {username} 升级为管理员，密码已按 ADMIN_PASSWORD 重置")
    else:
        cur.execute(
            "INSERT INTO users (username, email, hashed_password, role, is_active) VALUES (?,?,?,?,?)",
            (username, f"{username}@admin.local", hash_pw(password), "admin", 1)
        )
        print(f"管理员账号已创建: username={username}")

    conn.commit()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
