from flask import Flask, send_file, request,jsonify
import mysql.connector
from flask_cors import CORS
from io import StringIO
import time
import os

# US数据库配置
config_US = {
    'user': 'tk-quick',
    'password': 'TszieTCCddhsh4P2',
    'host': '192.168.3.4',
    'port': '3306',
    'database': 'tk-quick'
}

# LR数据库配置
config_LR = {
    'user': 'titok',
    'password': 'TrGHMWiDh2nYL56Y',
    'host': '152.53.33.145',
    'port': '3306',
    'database': 'titok'
}

app = Flask(__name__)
CORS(app)

# 创建数据库连接池
def create_connection_pool(config):
    return mysql.connector.pooling.MySQLConnectionPool(
        pool_name="mypool",
        pool_size=10,
        **config
    )

# 获取US数据库连接
us_pool = create_connection_pool(config_US)

# 获取LR数据库连接
lr_pool = create_connection_pool(config_LR)

# 连接US数据库
def get_connection_US():
    return mysql.connector.connect(
        user=config_US['user'],
        password=config_US['password'],
        host=config_US['host'],
        port=config_US['port'],
        database=config_US['database']
    )

# 连接LR数据库
def get_connection_LR():
    return mysql.connector.connect(
        user=config_LR['user'],
        password=config_LR['password'],
        host=config_LR['host'],
        port=config_LR['port'],
        database=config_LR['database']
    )

# 显示有的店铺下的category_id以及category_name以及description
@app.route('/get_category_info', methods=['GET'])
def get_category_info():
    try:
        # 获取数据库连接
        tr_connection = get_connection_LR()
        tr_cursor = tr_connection.cursor(dictionary=True)

        # 构造SQL查询
        query = """
            SELECT DISTINCT tsd.category_id, tpc.category_name, tpc.description
            FROM tiktok_shop_details AS tsd
            INNER JOIN titok_product_category AS tpc
            ON tsd.category_id = tpc.category_id
        """

        # 执行查询
        tr_cursor.execute(query)

        # 获取查询结果
        results = tr_cursor.fetchall()

        # 如果查询结果为空，返回提示
        if not results:
            return jsonify({"message": "No category data found."}), 404

        # 返回查询结果
        return jsonify({"categories": results}), 200

    except mysql.connector.Error as e:
        # 捕获并返回数据库连接相关的错误
        return jsonify({"error": str(e)}), 500

    finally:
        # 关闭数据库连接
        if 'tr_cursor' in locals():
            tr_cursor.close()
        if 'tr_connection' in locals():
            tr_connection.close()

# 更新链接为已使用状态
@app.route('/update_link_status', methods=['POST'])
def update_link_status():
    # 获取传入的JSON数据，必须包含 links 字段
    data = request.get_json()
    links = data.get('links', [])

    # 检查 links 是否为空
    if not links:
        return jsonify({"error": "No links provided"}), 400

    # 连接数据库
    try:
        us_connection = get_connection_US()
        us_cursor = us_connection.cursor()

        # 构造 SQL 更新语句
        query = """
            UPDATE category_links
            SET is_used = 1
            WHERE link IN (%s)
        """
        # 使用连接符构建 `IN` 中的占位符
        format_strings = ','.join(['%s'] * len(links))  # 根据链接数量生成占位符
        query = query % format_strings

        # 执行更新操作
        us_cursor.execute(query, tuple(links))
        us_connection.commit()

        # 返回更新成功的消息
        return jsonify({"message": f"Successfully updated {us_cursor.rowcount} links."}), 200

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # 关闭数据库连接
        if 'us_cursor' in locals():
            us_cursor.close()
        if 'us_connection' in locals():
            us_connection.close()

# 同步LR的数据到US数据库
@app.route('/synch_data')
def synch_data():
    try:
        # 获取LR数据库连接
        lr_connection = lr_pool.get_connection()
        lr_cursor = lr_connection.cursor(dictionary=True)

        # 执行查询以获取需要同步的数据
        query = """
        SELECT DISTINCT afp.raw_url, tsd.category_id
        FROM tiktok_publish_products AS tpp
        INNER JOIN amazon_filter_product AS afp ON tpp.amazon_filter_product_id = afp.id
        INNER JOIN tiktok_shop_details AS tsd ON tpp.seller_code = tsd.seller_code;
        """
        lr_cursor.execute(query)
        data_to_sync = lr_cursor.fetchall()

        # 获取US数据库连接
        us_connection = us_pool.get_connection()
        us_cursor = us_connection.cursor()

        # 先查询US数据库中所有已有的raw_url
        raw_urls = [row['raw_url'] for row in data_to_sync]
        if raw_urls:  # 确保有数据
            placeholders = ', '.join(['%s'] * len(raw_urls))  # 生成占位符
            check_query = f"SELECT link FROM category_links WHERE link IN ({placeholders})"
            us_cursor.execute(check_query, tuple(raw_urls))  # 传入参数时需要是元组
            existing_urls = set(row[0] for row in us_cursor.fetchall())
        else:
            existing_urls = set()

        # 准备批量插入的数据
        data_to_insert = [(row['category_id'], row['raw_url']) for row in data_to_sync if
                          row['raw_url'] not in existing_urls]

        if data_to_insert:
            # 批量插入
            insert_query = "INSERT INTO category_links (category_id, link) VALUES (%s, %s)"
            us_cursor.executemany(insert_query, data_to_insert)
            us_connection.commit()

        # 关闭连接
        lr_cursor.close()
        lr_connection.close()
        us_cursor.close()
        us_connection.close()

        return "数据同步完成"

    except mysql.connector.Error as err:
        print("Error:", err)
        return "数据库同步失败"

# 获取未使用的链接
@app.route('/get_unused_links', methods=['GET'])
def get_unused_links():
    # 获取category_id和数量参数
    category_id = request.args.get('category_id', type=int)
    limit = request.args.get('limit', default=100, type=int)

    if category_id is None:
        return "category_id is required", 400

    # 连接数据库
    try:
        us_connection = get_connection_US()
        us_cursor = us_connection.cursor(dictionary=True)

        # 查询未使用的链接
        query = """
            SELECT link 
            FROM category_links 
            WHERE category_id = %s AND is_used = 0
            LIMIT %s
        """

        us_cursor.execute(query, (category_id, limit))
        unused_links = us_cursor.fetchall()

        if not unused_links:
            return f"No unused links found for category_id {category_id}", 404

        # 将结果写入TXT文件，使用逗号分隔
        output = StringIO()
        links = [link['link'] for link in unused_links]
        output.write(', '.join(links))

        # 保存txt文件
        file_name = f"unused_links_category_{category_id}.txt"
        with open(file_name, 'w') as f:
            f.write(output.getvalue())

        # 返回生成的txt文件
        return send_file(file_name, as_attachment=True)

    except mysql.connector.Error as e:
        return f"Database error: {str(e)}", 500
    finally:
        # 关闭数据库连接
        if 'us_cursor' in locals():
            us_cursor.close()
        if 'us_connection' in locals():
            us_connection.close()

# 获取大类目订单统计数据
@app.route('/get_order_statistic_root_category', methods=['GET'])
def get_order_statistic_root_category():

    # 连接数据库
    try:
        lr_connection = get_connection_LR()
        lr_cursor = lr_connection.cursor(dictionary=True)

        # 查询
        query = """
            SELECT d.category_id, 
                   d.category_name, 
                   d.description,
                   ROUND(SUM(b.payment_total_amount), 2) AS userpay, 
                   ROUND(SUM(b.payment_total_amount + b.payment_platform_discount - (b.payment_shipping_fee_tax + b.payment_product_tax + IFNULL(e.money, 0))), 2) AS profit, 
                   ROUND(SUM(IFNULL(e.money, 0)), 2) AS chengben, 
                   COUNT(0) AS orderCount,
                   ROUND(SUM(b.payment_total_amount) / COUNT(0), 2) AS avgUserPrice,
                   ROUND(SUM(b.payment_total_amount + b.payment_platform_discount - (b.payment_shipping_fee_tax + b.payment_product_tax + IFNULL(e.money, 0))) / COUNT(0), 2) AS avgProfit,
                   ROUND(SUM(IFNULL(e.money, 0)) / COUNT(0), 2) AS avgChengben,
                   ROUND(SUM(b.payment_shipping_fee_tax) / COUNT(0), 2) AS avgfeeTax,
                   ROUND(SUM(b.payment_product_tax) / COUNT(0), 2) AS avgproductTax
            FROM tiktok_orders_items AS a
            INNER JOIN tiktok_orders AS b ON a.order_id = b.order_id
            INNER JOIN tiktok_shop_details AS c ON b.seller_code = c.seller_code
            INNER JOIN titok_product_category AS d ON c.category_id = d.category_id
            LEFT JOIN t_amazon_order AS e ON e.tiktok_order_id = b.id
            WHERE b.`status` = 'COMPLETED' 
            GROUP BY d.category_id, d.category_name, d.description
            ORDER BY profit DESC
        """

        lr_cursor.execute(query)
        results = lr_cursor.fetchall()

        if not results:
            return f"No result for order statistic in root category", 404

        # 返回结果
        return jsonify({"results": results}), 200
    except mysql.connector.Error as e:
        return f"Database error: {str(e)}", 500
    finally:
        # 关闭数据库连接
        if 'lr_cursor' in locals():
            lr_cursor.close()
        if 'lr_connection' in locals():
            lr_connection.close()


# 获取某个大类目订单统计数据
@app.route('/get_order_statistic_one_root_category', methods=['GET'])
def get_order_statistic_one_root_category():
    # 获取category_id参数
    category_id = request.args.get('category_id', type=int)

    if category_id is None:
        return "category_id is required", 400

    # 连接数据库
    try:
        lr_connection = get_connection_LR()
        lr_cursor = lr_connection.cursor(dictionary=True)

        # 查询
        query = """
            select g.category_id, g.category_name,g.description,
                   ROUND(SUM(b.payment_total_amount), 2) AS userpay, 
                   ROUND(SUM(b.payment_total_amount + b.payment_platform_discount - (b.payment_shipping_fee_tax + b.payment_product_tax + IFNULL(e.money, 0))), 2) AS profit, 
                   ROUND(SUM(IFNULL(e.money, 0)), 2) AS chengben, 
                   COUNT(0) AS orderCount,
                   ROUND(SUM(b.payment_total_amount) / COUNT(0), 2) AS avgUserPrice,
                   ROUND(SUM(b.payment_total_amount + b.payment_platform_discount - (b.payment_shipping_fee_tax + b.payment_product_tax + IFNULL(e.money, 0))) / COUNT(0), 2) AS avgProfit,
                   ROUND(SUM(IFNULL(e.money, 0)) / COUNT(0), 2) AS avgChengben,
                   ROUND(SUM(b.payment_shipping_fee_tax) / COUNT(0), 2) AS avgfeeTax,
                   ROUND(SUM(b.payment_product_tax) / COUNT(0), 2) AS avgproductTax
            from tiktok_orders_items as a
            inner join tiktok_orders as b on a.order_id = b.order_id
            inner join tiktok_shop_details as c on b.seller_code = c.seller_code
            inner join titok_product_category as d on c.category_id = d.category_id
            left join t_amazon_order as e on e.tiktok_order_id = b.id
            inner join amazon_filter_product as f on a.filter_product_id = f.id
            inner join titok_product_category as g on f.category_id =g.category_id
            where d.category_id = %s and  b.`status` = 'COMPLETED' 
            group by g.category_id, g.category_name,g.description
            order by profit desc
        """

        lr_cursor.execute(query, (category_id,))
        results = lr_cursor.fetchall()

        if not results:
            return f"No result for order statistic in one root category", 404

        # 返回结果
        return jsonify({"results": results}), 200
    except mysql.connector.Error as e:
        return f"Database error: {str(e)}", 500
    finally:
        # 关闭数据库连接
        if 'lr_cursor' in locals():
            lr_cursor.close()
        if 'lr_connection' in locals():
            lr_connection.close()

# 获取某个大类目订单明细
@app.route('/get_order_detail_one_root_category', methods=['GET'])
def get_order_detail_one_root_category():
    # 获取category_id参数
    category_id = request.args.get('category_id', type=int)

    if category_id is None:
        return "category_id is required", 400

    # 连接数据库
    try:
        lr_connection = get_connection_LR()
        lr_cursor = lr_connection.cursor(dictionary=True)

        # 查询
        query = """
            select b.order_id, g.category_id, g.category_name,g.description,
                ROUND(b.payment_total_amount, 2) AS userpay, 
                ROUND(b.payment_total_amount + b.payment_platform_discount - (b.payment_shipping_fee_tax + b.payment_product_tax + IFNULL(e.money, 0)), 2) AS profit,
                ROUND(IFNULL(e.money, 0), 2) AS chengben,
                ROUND(b.payment_shipping_fee_tax, 2) AS feeTax,
                ROUND(b.payment_product_tax, 2) AS productTax
            from tiktok_orders_items as a
            inner join tiktok_orders as b on a.order_id = b.order_id
            inner join tiktok_shop_details as c on b.seller_code = c.seller_code
            inner join titok_product_category as d on c.category_id = d.category_id
            left join t_amazon_order as e on e.tiktok_order_id = b.id
            inner join amazon_filter_product as f on a.filter_product_id = f.id
            inner join titok_product_category as g on f.category_id =g.category_id
            where d.category_id = %s and b.`status` = 'COMPLETED' 
            order by profit desc
        """

        lr_cursor.execute(query, (category_id,))
        results = lr_cursor.fetchall()

        if not results:
            return f"No result for order statistic in one root category", 404

        # 返回结果
        return jsonify({"results": results}), 200
    except mysql.connector.Error as e:
        return f"Database error: {str(e)}", 500
    finally:
        # 关闭数据库连接
        if 'lr_cursor' in locals():
            lr_cursor.close()
        if 'lr_connection' in locals():
            lr_connection.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=21312)
