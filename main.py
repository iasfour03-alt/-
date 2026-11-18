from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import psycopg2
from datetime import datetime

app = FastAPI(title="نظام نكتار ERP السحابي", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# الاتصال بقاعدة البيانات السحابية (تلقائياً من بيئة الاستضافة أو قاعدة محلية للتجربة)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///nektar_cloud.db")

def get_db_connection():
    # دعم لـ PostgreSQL السحابية أو SQLite المحلية
    if DATABASE_URL.startswith("postgres"):
        conn = psycopg2.connect(DATABASE_URL)
        return conn, "postgres"
    else:
        import sqlite3
        conn = sqlite3.connect("nektar_cloud.db", check_same_thread=False)
        return conn, "sqlite"

def init_db():
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    if db_type == "postgres":
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(50) NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                role VARCHAR(20) NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                barcode VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                flavor VARCHAR(50) NOT NULL,
                size VARCHAR(50) NOT NULL,
                selling_price REAL,
                stock_qty INT DEFAULT 0,
                expiry_date VARCHAR(20)
            )
        ''')
    else:
        cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, full_name TEXT, role TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT UNIQUE, name TEXT, flavor TEXT, size TEXT, selling_price REAL, stock_qty INT, expiry_date TEXT)')

    # إضافة المدير الافتراضي
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        if db_type == "postgres":
            cursor.execute("INSERT INTO users (username, password, full_name, role) VALUES (%s, %s, %s, %s)", ('admin', '1234', 'إبراهيم (المدير العام)', 'admin'))
            cursor.execute("INSERT INTO users (username, password, full_name, role) VALUES (%s, %s, %s, %s)", ('store', '1234', 'محمود (أمين المستودع)', 'store'))
        else:
            cursor.execute("INSERT INTO users (username, password, full_name, role) VALUES (?, ?, ?, ?)", ('admin', '1234', 'إبراهيم (المدير العام)', 'admin'))
            cursor.execute("INSERT INTO users (username, password, full_name, role) VALUES (?, ?, ?, ?)", ('store', '1234', 'محمود (أمين المستودع)', 'store'))
            
    conn.commit()
    cursor.close()
    conn.close()

init_db()

class LoginModel(BaseModel):
    username: str
    password: str

@app.post("/api/login")
def login(data: LoginModel):
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    if db_type == "postgres":
        cursor.execute("SELECT full_name, role FROM users WHERE username = %s AND password = %s", (data.username, data.password))
    else:
        cursor.execute("SELECT full_name, role FROM users WHERE username = ? AND password = ?", (data.username, data.password))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user:
        return {"status": "success", "full_name": user[0], "role": user[1]}
    raise HTTPException(status_code=401, detail="اسم المستخدم أو كلمة المرور غير صحيحة")

@app.get("/", response_class=HTMLResponse)
def home():
    return "<h1>النظام السحابي لنكتار ERP يعمل بكفاءة عالية على الإنترنت!</h1><p>استخدم تطبيق الواجهة للاتصال بهذا السيرفر.</p>"