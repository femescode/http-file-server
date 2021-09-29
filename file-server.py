#!/usr/bin/env python
# coding: utf-8

import os
import sys
import urllib
import codecs
import glob
import commands
import time
import re
import BaseHTTPServer
import SocketServer
import mimetypes
import json
import cgi
import socket
import io
import math

reload(sys)
sys.setdefaultencoding("utf-8")
mimetypes.init()

localip = ""
port = 8000
g_filepath = ""

def humansize(size):
    kb=1024
    mb=kb*1024
    gb=mb*1024
    tb=gb*1024
    if size>=tb:
        return "%.1fTB" % (float(size) / tb)
    elif size>=gb:
        return "%.1fGB" % (float(size) / gb)
    elif size>=mb:
        return "%.1fMB" % (float(size) / mb)
    elif size>=kb:
        return "%.1fKB" % (float(size) / kb)
    else:
        return "%dB" % size

def is_text(size, fn):
    if size <= 2097152 and re.search('\.(txt|csv|log|sh|properties|conf|cfg|md)$', fn, re.I):
        return True
    return False

def is_jpg(size, fn):
    return re.search('\.(jpg|jpeg)$', fn, re.I)

def is_png(size, fn):
    return re.search('\.(png)$', fn, re.I)

def is_svg(size, fn):
    return re.search('\.(svg)$', fn, re.I)

def transDicts(params):
    dicts={}
    if len(params)==0:
        return
    params = params.split("&")
    for param in params:
        keyvalue = param.split("=")
        key = keyvalue[0]
        value = keyvalue[1]
        value = urllib.unquote_plus(value).decode("utf-8", "ignore")
        dicts[key] = value
    return dicts

class HTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def end_headers (self):
        self.send_header("Access-Control-Allow-Origin", "*")
        BaseHTTPServer.BaseHTTPRequestHandler.end_headers(self)

    def do_GET(self):
        query = urllib.splitquery(self.path)
        path = urllib.unquote_plus(query[0]).decode("utf-8", "ignore")
        queryParams = {}

        if "?" in self.path:
            if query[1]:
                queryParams = transDicts(query[1])

        fn = "%s%s" % (g_filepath, path)
        fn = urllib.unquote_plus(fn).decode("utf-8", "ignore")
        fn = fn.replace("/",os.sep)

        content = ""
        self.send_response(200)
        # 下载文件处理
        if os.path.isfile(fn):
            filesize = os.path.getsize(fn)
            if is_text(filesize, fn):
                self.send_header("Content-Type",'text/plain; charset=utf-8')
                self.send_header("Content-disposition",'inline')
            elif is_jpg(filesize, fn):
                self.send_header("Content-Type",'image/jpeg')
                self.send_header("Content-disposition",'inline')
            elif is_png(filesize, fn):
                self.send_header("Content-Type",'image/png')
                self.send_header("Content-disposition",'inline')
            elif is_svg(filesize, fn):
                self.send_header("Content-Type",'image/svg+xml')
                self.send_header("Content-disposition",'inline')
            else:
                self.send_header("Content-Type",'application/octet-stream')
                self.send_header("Content-disposition",'attachment')
            self.send_header("Content-Length",filesize)
            self.end_headers()
            with io.open(fn, "rb") as f:
                while True:
                    data = f.read(10485760)
                    if not data:
                        break
                    self.wfile.write(data)
            return
        # 删除文件处理
        elif path.endswith('/delete'):
            fn = fn[0:len(fn)-len('/delete')]
            if os.path.isfile(fn):
                os.remove(fn)
                content = json.dumps({"result":0, "msg":"删除成功！"})
            elif os.path.isdir(fn):
                if len(os.listdir(fn)) == 0:
                    os.rmdir(fn)
                    content = json.dumps({"result":0, "msg":"删除成功！"})
                else:
                    content = json.dumps({"result":1, "msg":"删除失败，目录中存在文件，无法删除！"})
            else:
                content = json.dumps({"result":2, "msg":"删除失败，未找到该文件！"})
            self.send_header("Content-Type","application/json; charset=UTF-8")
            self.send_header("Content-Length", len(content.encode('UTF-8')))
        # 列出文件处理
        elif os.path.isdir(fn):
            html_sb = []
            style = '''
                    .delete{
                        color: red;
                        text-decoration: none;
                        padding-right: 10px;
                    }
                    .one{min-width:180px;float:left;}
                    .two{min-width:70px;float:left;}
                '''
            script = '''
                    function deleteFunc(url){
                        var r=confirm("确定删除吗?");
                        if (r){
                            var xmlhttp=new XMLHttpRequest();
                            xmlhttp.onreadystatechange=function(){
                                if (xmlhttp.readyState==4 && xmlhttp.status==200){
                                    var res=JSON.parse(xmlhttp.responseText);
                                    if(res.result == 0){
                                        location.reload();
                                    }else{
                                        alert(res.msg);
                                    }
                                }
                            }
                            xmlhttp.open("GET",url,true);
                            xmlhttp.send();
                        }
                    }
                '''
            dirname = re.sub(r'^/|/$', '', path)
            html_sb.append('<header><title>%s</title><style>%s</style><script>%s</script>'%(path,style,script))
            html_sb.append('<h1>Directory listing for '+path+'</h1>')
            html_sb.append('<ol>')
            if dirname != '':
                dirname = re.sub(r'$', '/', dirname)
            html_sb.append('<li>下载命令：<code>curl -LO http://%s:%s/%stest.txt</code></li>'%(localip,port,dirname))
            html_sb.append('<li>上传命令(小文件)：<code>find test.txt -maxdepth 1 -type f|xargs -i -n1 curl http://%s:%s/%s -F file=@{}|cat</code></li>'%(localip,port,dirname))
            html_sb.append('<li>上传命令(大文件)：<code>find test.txt -maxdepth 1 -type f|while read l;do n=$(basename "$l"|tr -d "\\n"|xxd -ps|sed "s/../%%&/g");curl "http://%s:%s/%s$n" --data-binary @"$l"|cat; done</code></li>'%(localip,port,dirname))
            html_sb.append('</ol>')
            html_sb.append('<hr>')
            html_sb.append('<ul>')
            for filename in os.listdir(fn):
                if filename[0] != ".":
                    filepath = "%s%s%s" % (fn, os.sep, filename)
                    if os.path.isdir(filepath):
                        deletehtml='<a href="javascript:deleteFunc(\'{}/delete\')" class="delete">×</a>'.format(filename)
                        filename += os.sep
                    else:
                        deletehtml='<a href="javascript:deleteFunc(\'{}/delete\')" class="delete">×</a>'.format(filename)
                    mtime = os.path.getmtime(filepath)
                    filetime = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(mtime))
                    filesize = os.path.getsize(filepath)
                    html_sb.append('<li><div class="one">{}</div><div class="two">{}</div>{}<a href="{}">{}</a></li>'.format(filetime,humansize(filesize),deletehtml,filename,filename))
            html_sb.append('</ul>')
            html_sb.append('<hr>')
            content = '\n'.join(html_sb)
            self.send_header("Content-Type","text/html; charset=UTF-8")
            self.send_header("Content-Length", len(content.encode('UTF-8')))
        else:
            content = "<h1>404<h1>"
            self.send_header("Content-Type","text/html; charset=UTF-8")
            self.send_header("Content-Length", len(content.encode('UTF-8')))

        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        query = urllib.splitquery(self.path)
        path = query[0]
        queryParams = {}

        if "?" in self.path:
            if query[1]:
                queryParams = transDicts(query[1])

        resultdict = {"result":0, "msg":"OK"}
        r, info = self.deal_post_data(path, queryParams)
        if not r:
            resultdict["result"] = 1
            resultdict["msg"] = info
        else:
            resultdict["result"] = 0
            resultdict["files"] = info

        content = json.dumps(resultdict) + "\n"
        self.send_response(200)
        self.send_header("Content-Type","application/json; charset=UTF-8")
        self.send_header("Content-Length", len(content.encode('UTF-8')))
        self.end_headers()
        self.wfile.write(content)

    def deal_post_data(self,path, queryParams):
        dirname = path
        if dirname is None:
            dirname = ''
        dirname = dirname.strip()
        dirname = re.sub(r'^/', '', dirname)
        dirname = "%s%s" % (g_filepath, dirname)

        ctype, pdict = cgi.parse_header(self.headers['Content-Type'])
        if ctype != 'multipart/form-data':
            dirname = re.sub(r'/$', '', dirname)
            if dirname == '' or os.path.isdir(dirname):
                return (False, "%s is dir, cannot write file! " % dirname)
            if dirname.find('/') > -1:
                idx = dirname.rfind('/')
                dirname = dirname[0:idx] + urllib.unquote_plus(dirname[idx:]).decode("utf-8", "ignore")

            remainLength = int(self.headers['Content-Length'])
            buflen = 10485760
            with io.open(dirname, "wb+") as f:
                while remainLength > 0:
                    readlen = min(remainLength, buflen)
                    data = self.rfile.read(readlen)
                    if not data:
                        break
                    f.write(data)
                    remainLength -= readlen
            return (True, dirname)
        else:
            dirname = re.sub(r'(?!/)$', '/', dirname)
            if dirname != '' and not os.path.exists(dirname):
                os.makedirs(dirname)

            form = cgi.FieldStorage( fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD':'POST', 'CONTENT_TYPE':self.headers['Content-Type'], })
            try:
                filelist = form["file"]
                if not isinstance(form["file"], list):
                    filelist = list()
                    filelist.append(form["file"])
                for record in filelist:
                    filepath = "%s%s"%(dirname, record.filename)
                    with io.open(filepath, "wb") as fw:
                        while True:
                            data = record.file.read(10485760)
                            if not data:
                                break
                            fw.write(data)
                return (True, ','.join([record.filename for record in filelist]))
            except IOError:
                return (False, "Can't create file to write, do you have permission to write? %s" % filepath)

class ThreadingHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass

def run(port):
    print("HTTP File Server Started at : http://%s:%s/" % (localip,port))
    server_address = ("", port)
    httpd = ThreadingHTTPServer(("", port), HTTPRequestHandler)
    httpd.serve_forever()

def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception as e:
        print(e)
        ip = '0.0.0.0'
    finally:
        s.close()

    return ip

if __name__=="__main__":
    g_filepath = "./files/"
    if len(sys.argv)>=2:
        g_filepath = sys.argv[1]
    if g_filepath[-1]!=os.sep:
        g_filepath += os.sep
    g_filepath = g_filepath.replace("/",os.sep)

    localip = get_host_ip()
    port = 8000
    if len(sys.argv)==3:
        port = int(sys.argv[2])

    run(port)
