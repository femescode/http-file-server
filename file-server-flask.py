from flask import Flask,request,make_response,abort,send_file,send_from_directory
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

@app.route('/user/<int:user_id>', methods=['GET','POST'])
def index(user_id=1234):
    try:
        return {
            "path": request.path,
            "method": request.method,
            "Content-Type": request.headers.get('Content-Type'), 
            "user_id": user_id,
            'age': request.args.get('age', ''),                 # url中的参数
            "username": request.form.get('username',''),        # application/x-www-form-urlencoded
            'json': request.json,                               # application/json
            'data': request.data.decode('utf8')                 # 除以上场景才有值，二进制数据
        }
    except Exception as e:
        print(e)
        abort(make_response("error", 500))

@app.route('/upload/<path:subdir>', methods=['POST'])
def upload_file(subdir=''):
    filepath = os.path.join('files', subdir)
    if not os.path.exists(filepath):
        os.makedirs(filepath)
    for f in request.files.values():   # multipart/form-data
        f.save(os.path.join(filepath, secure_filename(f.filename)))
    return 'ok'

@app.route('/download/<path:subdir>', methods=['GET'])
def download_file(subdir=''):
    filepath = os.path.join('files', subdir)
    if os.path.isfile(filepath):
        return send_from_directory('files', subdir, as_attachment=True)
    abort(404)

app.run(host='0.0.0.0', port=8080)