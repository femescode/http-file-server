#!/bin/bash 

to_html(){
    filepath="$1"
    content="$2"
    echo '<!DOCTYPE HTML">
    <html>
    <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Directory listing for '"$filepath"'</title>
    <style>
    .one{min-width:180px;float:left;}
    .two{min-width:70px;float:left;}
    </style>
    </head>
    <body>
    <h1>Directory listing for '"$filepath"'</h1>
    <ol>
    <li>下载命令：<code>curl -LO http://{{serverip}}:{{port}}/{{dirpath}}/test.txt</code></li>
    <li>上传命令(大文件)：<code>find test.txt -maxdepth 1 -type f|while read l;do n=$(basename "$l"|tr -d "\\n"|xxd -ps|sed "s/../%&/g");curl "http://{{serverip}}:{{port}}/{{dirpath}}/$n" --data-binary @"$l"|cat; done</code></li>
    </ol>
    <hr>
    <ul>
    '"$content"'
    </ul>
    <hr>
    </body>
    </html>'
}

print_content(){
    respcode=$1
    contenttype="$2"
    content="$3"
    length=$(echo -n "$content"|wc -c)
    printf "HTTP/1.1 $respcode OK\r\n$contenttype\r\nContent-Length: $length\r\n\r\n"
    echo -n "$content"
}

cat_file(){
    respcode=$1
    contenttype="$2"
    filepath="$3"
    length=$(stat -c %s "$filepath")
    printf "HTTP/1.1 $respcode OK\r\n$contenttype\r\nContent-Length: $length\r\n\r\n"
    cat "$filepath"
}

is_text(){
    filepath="$1"
    filesize=$(stat -c %s "$filepath")
    if [[ $filesize -le 2097152 && "$filepath" =~ \.(txt|csv|log|sh|properties|conf|cfg|md)$ ]]; then
        return 0
    fi
    return 1
}

is_jpg(){
    filepath="$1"
    if [[ "$filepath" =~ \.(jpg|jpeg)$ ]]; then
        return 0
    fi
    return 1
}

is_png(){
    filepath="$1"
    if [[ "$filepath" =~ \.(png)$ ]]; then
        return 0
    fi
    return 1
}

is_svg(){
    filepath="$1"
    if [[ "$filepath" =~ \.(svg)$ ]]; then
        return 0
    fi
    return 1
}

while read line; do
    getpat='^GET /(([^/]+/?)*) HTTP/1.1'
    if [[ "$line" =~ $getpat ]]; then
        # 获取下载路径
        filepath=$("urlencode" -d "${BASH_REMATCH[1]:-.}")
        echo "--> GET: $filepath" > /dev/tty;
        if [[ -d "$filepath" ]]; then
            # 列出目录
            content=$(ls -lthQp --time-style='+%FT%T' "$filepath"|awk -v FPAT='"([^"\\\\]|\\\\.|"")*"/?|\\S+' 'NR>1{
                s=gensub(/"/,"","g",$7);
                printf "<li><div class=\"one\">%s</div><div class=\"two\">%s</div><a href=\"%s\">%s</a></li>\n",$6,$5,s,s
                }');
            content=$(to_html "$filepath" "$content")
            print_content 200 "Content-Type: text/html; charset=utf-8" "$content"
        elif [[ -f "$filepath" ]]; then
            # 查看或下载文件
            if is_text "$filepath";then
                cat_file 200 $'Content-Type: text/plain; charset=utf-8\r\nContent-disposition: inline' "$filepath"
            elif is_jpg "$filepath";then
                cat_file 200 $'Content-Type: image/jpeg\r\nContent-disposition: inline' "$filepath"
            elif is_png "$filepath";then
                cat_file 200 $'Content-Type: image/png\r\nContent-disposition: inline' "$filepath"
            elif is_svg "$filepath";then
                cat_file 200 $'Content-Type: image/svg+xml\r\nContent-disposition: inline' "$filepath"
            else
                cat_file 200 $'Content-Type: application/octet-stream\r\nContent-disposition: attachment' "$filepath"
            fi
        else
            print_content 404 "Content-Type: text/html; charset=utf-8" "404"
        fi
    fi
    postpat='^POST /(([^/]+/?)*) HTTP/1.1'
    if [[ "$line" =~ $postpat ]]; then
        # 获取上传路径
        filepath=$("urlencode" -d "${BASH_REMATCH[1]:-.}")
        echo "--> POST: $filepath" > /dev/tty;
        # 获取Content-Length并读完http header
        clpat='Content-Length: (\w+)'
        while read h; do
            if [[ "$h" =~ $clpat ]]; then
                contentLength="${BASH_REMATCH[1]}"
            elif [[ "$h" =~ ^[[:space:]]+$ ]]; then
                break;
            fi
        done
        # 保存上传的文件
        if [[ "$contentLength" && ! -d "$filepath" ]]; then
            head -c "$contentLength" > "$filepath"
            print_content 200 "Content-Type: text/html; charset=utf-8" "$filepath upload done!"
            unset contentLength
        fi
    fi
done