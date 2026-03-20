from flask import Flask, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# 设置上传目录
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'Public', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 允许上传的最大文件大小（这里是 2GB）
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024

# 允许的文件扩展名，可自行修改
ALLOWED_EXTENSIONS = {'jpg', 'png', 'gif', 'mp4', 'zip', 'pdf', 'txt', 'docx', 'xlsx', 'dump'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return '''
    <h2>文件上传测试</h2>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file"><br><br>
        <input type="submit" value="上传">
    </form>
    '''

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 0, 'message': '没有文件部分'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 0, 'message': '未选择文件'})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        file_url = f"/uploads/{filename}"
        return jsonify({'status': 1, 'message': '上传成功', 'url': file_url})

    return jsonify({'status': 0, 'message': '文件类型不允许'})

# 提供静态访问（访问上传后的文件）
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    # 在局域网可访问
    print("🚀 文件上传服务启动中：请访问 http://<本机局域网IP>:8900")
    app.run(host='0.0.0.0', port=8900, debug=True)
