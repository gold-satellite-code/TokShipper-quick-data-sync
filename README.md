# TokShipper-quick-data-sync



执行环境指令：

```
conda create --name data-sync python=3.9

conda activate data-sync

pip freeze > requirements.txt
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
docker build -t TokShipper-quick-data-sync .

docker run -d -p 2467:2467 --name TokShipper-quick-data-sync TokShipper-quick-data-sync
```

