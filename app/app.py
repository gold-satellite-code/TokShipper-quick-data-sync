from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import mysql.connector
import time

# A数据库配置
config_a = {
    'user': 'tk-quick',
    'password': 'TszieTCCddhsh4P2',
    'host': '192.168.3.4',
    'port': '3306',
    'database': 'tk-quick'
}

# B数据库配置
config_b = {
    'user': 'root',
    'password': '123456',
    'host': 'localhost',
    'port': '3306',
    'database': 'test'
}

app = Flask(__name__)

# 连接A数据库
def get_connection_a():
    return mysql.connector.connect(
        user=config_a['user'],
        password=config_a['password'],
        host=config_a['host'],
        port=config_a['port'],
        database=config_a['database']
    )

# 连接B数据库
def get_connection_b():
    return mysql.connector.connect(
        user=config_b['user'],
        password=config_b['password'],
        host=config_b['host'],
        port=config_b['port'],
        database=config_b['database']
    )

# 同步A表数据到B表
def sync_data():
    try:
        conn_a = get_connection_a()
        cursor_a = conn_a.cursor(dictionary=True)

        conn_b = get_connection_b()
        cursor_b = conn_b.cursor()

        # 查询A表中的数据
        cursor_a.execute("SELECT * FROM students")
        rows_a = cursor_a.fetchall()

        # 遍历A表数据并同步到B表
        for row in rows_a:
            # 检查B表是否已有该记录
            cursor_b.execute("SELECT * FROM students WHERE id = %s", (row['id'],))
            result_b = cursor_b.fetchone()

            if result_b:
                # 如果B表有该记录，更新它
                cursor_b.execute(
                    "UPDATE students SET name = %s, age = %s, grade = %s WHERE id = %s",
                    (row['name'], row['age'], row['grade'], row['id'])
                )
                print(f"更新记录：ID = {row['id']}, Name = {row['name']}, Age = {row['age']}, Grade = {row['grade']}")
            else:
                # 如果B表没有该记录，插入新记录
                cursor_b.execute(
                    "INSERT INTO students (id, name, age, grade) VALUES (%s, %s, %s, %s)",
                    (row['id'], row['name'], row['age'], row['grade'])
                )
                print(f"新增记录：ID = {row['id']}, Name = {row['name']}, Age = {row['age']}, Grade = {row['grade']}")

        # 提交B表的变更
        conn_b.commit()

        # 关闭连接
        cursor_a.close()
        cursor_b.close()
        conn_a.close()
        conn_b.close()

    except Exception as e:
        print(f"同步失败: {e}")

# 设置定时任务，每分钟同步一次数据
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=sync_data, trigger="interval", seconds=2)
    scheduler.start()

# 启动Flask应用
@app.route('/')
def index():
    return "Flask应用正在运行，数据库同步任务正在执行..."

if __name__ == '__main__':
    start_scheduler()
    app.run(debug=True, host='0.0.0.0', port=21312)
