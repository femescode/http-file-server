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

reload(sys)
sys.setdefaultencoding("utf-8")
mimetypes.init()

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
        if os.path.isfile(fn):
            self.send_header("content-type",'application/octet-stream')
            f = open(fn, "rb")
            content = f.read()
            f.close()
        elif os.path.isdir(fn):
            self.send_header("content-type","text/html")
            filelist = []
            filelist.append('<h1>Directory listing for '+path+'</h1>')
            filelist.append('<hr>')
            filelist.append('<ul>')
            for filename in os.listdir(fn):
                if filename[0] != ".":
                    filepath = "%s%s%s" % (fn, os.sep, filename)
                    if os.path.isdir(filepath):
                        filename += os.sep
                    mtime = os.path.getmtime(filepath)
                    filelist.append('<li><a href="{}">{}</a></li>'.format(filename,filename))
            filelist.append('</ul>')
            filelist.append('<hr>')
            content = '\n'.join(filelist)
        else:
            print(g_filepath, path, fn)
            content = "<h1>404<h1>"
            self.send_header("content-type","text/html")

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
            resultdict.result = 3
            resultdict.msg = "No this API."

        content = json.dumps(resultdict)
        self.send_response(200)
        self.send_header("content-type","application/json")
        self.end_headers()
        self.wfile.write(content)

    def deal_post_data(self,queryParams):
        dirname = queryParams.get("dirname")
        if dirname is None:
            dirname = ''
        dirname = "%s%s" % (g_filepath, dirname)
        if not os.path.exists(dirname):
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
    print "HTTP File Server Started at port:", port
    server_address = ("", port)
    httpd = ThreadingHTTPServer(("", port), HTTPRequestHandler)
    httpd.serve_forever()

if __name__=="__main__":
    g_filepath = "./files/"
    if len(sys.argv)>=2:
        g_filepath = sys.argv[1]
    if g_filepath[-1]!=os.sep:
        g_filepath += os.sep
    g_filepath = g_filepath.replace("/",os.sep)

    port = 8000
    if len(sys.argv)==3:
        port = int(sys.argv[2])

    run(port)
