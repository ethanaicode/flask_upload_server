from flask import Flask, request, jsonify, send_from_directory, render_template
import os
import re

app = Flask(__name__)

# 设置上传目录
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'Public', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 允许上传的最大文件大小（这里是 2GB）
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024

# 默认启用文件类型校验；如果需要允许所有文件类型上传，可以将下面的值设置为 True
app.config['ALLOW_ALL_FILE_TYPES'] = True

# 允许的文件扩展名，可自行修改
ALLOWED_EXTENSIONS = {'jpg', 'png', 'gif', 'mp4', 'zip', 'pdf', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'dump', 'dat'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_filename(filename):
    """
    支持中文的安全文件名处理函数
    保留中文、英文、数字、下划线、横线和点号，移除其他不安全字符
    """
    # 移除路径分隔符和其他危险字符
    filename = filename.replace('\\', '').replace('/', '')
    # 只保留安全字符：中文、字母、数字、下划线、横线、点号
    filename = re.sub(r'[^\w\u4e00-\u9fa5.-]', '_', filename)
    # 移除开头的点号（防止隐藏文件）
    filename = filename.lstrip('.')
    # 如果文件名为空，使用默认名称
    if not filename:
        filename = 'unnamed_file'
    return filename


def get_unique_filename(filename):
    """
    当同名文件已存在时，自动追加序号，避免覆盖已有文件。
    例如: file.txt -> file_1.txt -> file_2.txt
    """
    base_name, ext = os.path.splitext(filename)
    candidate = filename
    index = 1

    while os.path.exists(os.path.join(UPLOAD_FOLDER, candidate)):
        candidate = f"{base_name}_{index}{ext}"
        index += 1

    return candidate

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    files = request.files.getlist('files')

    # 向后兼容: 如果前端仍传单文件字段 file，也可正常处理
    if not files and 'file' in request.files:
        files = [request.files['file']]

    if not files:
        return jsonify({'status': 0, 'message': '没有文件部分', 'results': []}), 400

    allow_any_type = app.config.get('ALLOW_ALL_FILE_TYPES', False)
    results = []

    for file in files:
        original_filename = file.filename or ''
        if original_filename == '':
            results.append({
                'status': 0,
                'message': '未选择文件',
                'url': '',
                'filename': '',
                'original_filename': '',
            })
            continue

        if not (allow_any_type or allowed_file(original_filename)):
            results.append({
                'status': 0,
                'message': '文件类型不允许',
                'url': '',
                'filename': '',
                'original_filename': original_filename,
            })
            continue

        safe_name = safe_filename(original_filename)
        filename = get_unique_filename(safe_name)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        file_url = f"/uploads/{filename}"

        results.append({
            'status': 1,
            'message': '上传成功',
            'url': file_url,
            'filename': filename,
            'original_filename': original_filename,
        })

    success_count = sum(1 for item in results if item['status'] == 1)
    fail_count = len(results) - success_count

    overall_status = 1 if success_count > 0 else 0
    summary_message = f"成功 {success_count} 个，失败 {fail_count} 个"

    return jsonify({
        'status': overall_status,
        'message': summary_message,
        'success_count': success_count,
        'fail_count': fail_count,
        'results': results,
    })

# 提供静态访问（访问上传后的文件）
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    # 在局域网可访问
    print("File upload server started: http://<LAN-IP>:8900")
    app.run(host='0.0.0.0', port=8900, debug=False)
