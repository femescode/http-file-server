# HTTP File Server

**http-file-server** 是用 python 实现的 HTTP 文件服务器，支持上传和下载文件。

## 运行

```bash
$ python file-server.py files 8001
```

其中第一个参数 `files` 是存放文件的路径，第二个参数 `8001` 是 HTTP 服务器端口。

## 接口

### 1. 下载文件

```bash
curl -LO http://localhost:8001/test/test.txt
```

### 2. 上传文件

```bash
curl http://localhost:8001/upload?dirname=test/ -F "file=@./test.txt"
```
