# TokShipper-quick-data-sync



执行环境指令：

```
conda create --name data-sync python=3.9

conda activate data-sync

pip freeze > requirements.txt

pip install -r requirements.txt
```

执行测试SQL：

```
CREATE TABLE students (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    age INT,
    grade VARCHAR(50)
);

```

执行docker指令

```
docker build -t tokshipper-quick-data-sync .

docker run -d -p 21312:21312 --name tokshipper-quick-data-sync tokshipper-quick-data-sync
```

