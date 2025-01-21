# 使用官方 Python 镜像作为基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 将当前目录内容复制到容器中的 /app 目录
COPY . /app

# 安装依赖
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 开放容器的5000端口（Flask默认端口）
EXPOSE 2467

# 设置环境变量，确保Flask在生产环境中运行
ENV FLASK_ENV=production

# 设置 Flask 应用入口
CMD ["python", "app.py"]
