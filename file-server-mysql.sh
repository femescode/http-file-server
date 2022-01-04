#!/bin/bash 

to_html(){
    content="$1"
    echo '
<!DOCTYPE HTML>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>simple mysql web client</title>
    <style>
        #sql { width: 600px; height: 100px; }
        #sql_result { overflow: auto; margin-top:8px; }
        table { border-collapse: collapse; overflow-wrap: break-word; }
        th { max-width: 200px; padding: 0 8px; }
        td { max-width: 200px; padding: 0 8px; }
    </style>
    <script>
        function query_sql() {
            xmlhttp = new XMLHttpRequest();
            xmlhttp.open("GET", "/sql/" + encodeURIComponent(document.getElementById("sql").value), false);
            xmlhttp.send();
            document.getElementById("sql_result").innerHTML = xmlhttp.responseText;
        }
        function export_tsv() {
            window.location.href="/csv/" + encodeURIComponent(document.getElementById("sql").value)
        }
    </script>
</head>
<body>
    <h1>simple mysql web client</h1>
    <textarea id="sql"></textarea>
    <button type="button" onclick="javascript:query_sql()">查询</button>
    <button type="button" onclick="javascript:export_tsv()">导出tsv</button>
    <div id="sql_result">
        '"$content"'
    </div>
</body>
</html>
    '
}

response_content(){
    content="$1"
    length=$(echo -n "$content"|wc -c)
    echo -ne "HTTP/1.1 200 OK\r\n"
    echo -ne "Content-Type: text/html; charset=utf-8\r\n"
    echo -ne "Content-Length: $length\r\n"
    echo -ne "\r\n"
    echo -n "$content"
}

response_stream(){
    length="$1"
    filename="$2"
    echo -ne "HTTP/1.1 200 OK\r\n"
    echo -ne "Content-Type: application/octet-stream\r\n" 
    echo -ne "Content-disposition: attachment;filename=$filename\r\n"
    echo -ne "Content-Length: $length\r\n" 
    echo -ne "\r\n"
    cat
}

while read line; do
    getpat='^GET /(sql|csv)/(([^/]+/?)*) HTTP/1.1'
    if [[ "$line" =~ $getpat ]]; then
        action="${BASH_REMATCH[1]}"
        # 获取sql
        sql=$(echo "${BASH_REMATCH[2]}"|sed 's/%/\\x/g'|xargs -d"\n" echo -e)
        echo "--> GET: $action $sql" > /dev/tty;
        if [[ "$action" == "sql" ]]; then
            # 查询
            content=$(mysql -h localhost -P 3961 -u root --default-character-set utf8 -A -Ddemo -U -H -e "$sql")
            response_content "$content"
        else
            # 导出
            content=$(mysql -h localhost -P 3961 -u root --default-character-set utf8 -A -Ddemo -U -e "$sql")
            length=$(echo -n "$content"|wc -c)
            echo -n "$content" | response_stream "$length" "export_$(date +%FT%T).tsv"
        fi
    elif [[ "$line" =~ ^GET\  ]]; then
        html=$(to_html)
        response_content "$html"
    fi
done