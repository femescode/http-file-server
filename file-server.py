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

reload(sys)
sys.setdefaultencoding("utf-8")
mimetypes.init()

localip = ""
port = 8000
g_filepath = ""

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
        self.send_header("access-control-allow-origin", "*")
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
            self.send_header("content-type",'application/octet-stream')
            self.send_header("content-length",filesize)
            f = open(fn, "rb")
            content = f.read()
            f.close()
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
            self.send_header("content-type","application/json; charset=UTF-8")
        # 列出文件处理
        elif os.path.isdir(fn):
            self.send_header("content-type","text/html; charset=UTF-8")
            html_sb = []
            html_sb.append(
                '''<style>
                    .delete{
                        color: red;
                        text-decoration: none;
                        padding-right: 10px;
                    }
                </style>''')
            html_sb.append(
                '''<script>
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
                </script>''')
            html_sb.append('<h1>Directory listing for '+path+'</h1>')
            html_sb.append('<ol>')
            dirname = re.sub(r'^/|/$', '', path)
            if dirname == '':
                html_sb.append('<li>下载命令：<code>curl -LO http://%s:%s/test.txt</code></li>'%(localip,port))
                html_sb.append('<li>上传命令：<code>curl http://%s:%s/upload -F file=@./test.txt</code></li>'%(localip,port))
            else:
                html_sb.append('<li>下载命令：<code>curl -LO http://%s:%s/%s/test.txt</code></li>'%(localip,port,dirname))
                html_sb.append('<li>上传命令：<code>curl http://%s:%s/upload?dirname=%s/ -F file=@./test.txt</code></li>'%(localip,port,dirname))
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
                    html_sb.append('<li>{}<a href="{}">{}</a></li>'.format(deletehtml,filename,filename))
            html_sb.append('</ul>')
            html_sb.append('<hr>')
            content = '\n'.join(html_sb)
        else:
            content = "<h1>404<h1>"
            self.send_header("content-type","text/html; charset=UTF-8")

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
        if path=="/upload":
            r, info = self.deal_post_data(queryParams)
            if not r:
                resultdict.result = 1
                resultdict.msg = info
        else:
            resultdict.result = 2
            resultdict.msg = "No this API."

        content = json.dumps(resultdict)
        self.send_response(200)
        self.send_header("content-type","application/json; charset=UTF-8")
        self.end_headers()
        self.wfile.write(content)

    def deal_post_data(self,queryParams):
        dirname = queryParams.get("dirname")
        if dirname is None:
            dirname = ''
        dirname = dirname.strip()
        dirname = re.sub(r'(?!/)$', '/', dirname)
        dirname = re.sub(r'^/', '', dirname)
        dirname = "%s%s" % (g_filepath, dirname)
        if dirname != '' and not os.path.exists(dirname):
            os.makedirs(dirname)

        ctype, pdict = cgi.parse_header(self.headers['Content-Type'])
        if ctype != 'multipart/form-data':
            return (False, "request is not a multipart/form-data.")

        form = cgi.FieldStorage( fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD':'POST', 'CONTENT_TYPE':self.headers['Content-Type'], })
        try:
            if isinstance(form["file"], list):
                for record in form["file"]:
                    filepath = "%s%s"%(dirname, record.filename)
                    open(filepath, "wb").write(record.file.read())
            else:
                filepath = "%s%s"%(dirname, form["file"].filename)
                open(filepath, "wb").write(form["file"].file.read())
            return (True, "Files uploaded")
        except IOError:
                return (False, "Can't create file to write, do you have permission to write? %s"%filepath)

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
