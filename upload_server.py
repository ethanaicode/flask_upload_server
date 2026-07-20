from functools import wraps
import hmac
from flask import Flask, request, jsonify, send_from_directory, render_template, session
import os
import re
import shutil
from datetime import datetime
from urllib.parse import quote

from dotenv import find_dotenv, load_dotenv

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

cwd_dotenv = find_dotenv(usecwd=True)
if cwd_dotenv:
    load_dotenv(cwd_dotenv, override=True)
load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)


def get_env_value(*names, default=''):
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return value
    return default


def get_bool_env(*names, default=False):
    value = get_env_value(*names, default='')
    if value == '':
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def get_int_env(*names, default):
    value = get_env_value(*names, default='')
    if value == '':
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def resolve_path_from_env(raw_path, base_dir=BASE_DIR):
    raw_path = (raw_path or '').strip()
    if not raw_path:
        return ''

    expanded_path = os.path.expanduser(raw_path)
    if os.path.isabs(expanded_path):
        return os.path.abspath(expanded_path)

    return os.path.abspath(os.path.join(base_dir, expanded_path))

# 设置上传目录
UPLOAD_FOLDER = resolve_path_from_env(
    get_env_value('UPLOAD_FOLDER', 'UPLOAD_DIR', 'UPLOAD_PATH', default='')
) or os.path.join(BASE_DIR, 'Public', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 允许上传的最大文件大小（这里是 2GB）
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024

app.config['SECRET_KEY'] = get_env_value(
    'SECRET_KEY',
    'FLASK_SECRET_KEY',
    default='flask-upload-server-secret-key'
)

app.config['ACCESS_PASSWORD'] = get_env_value(
    'ACCESS_PASSWORD',
    'UPLOAD_PASSWORD',
    'PAGE_PASSWORD',
    default=''
)

app.config['STARTUP_MODE'] = get_env_value('STARTUP_MODE', 'RUN_MODE', default='lan').strip().lower()
app.config['STARTUP_HOST'] = get_env_value('HOST', 'BIND_HOST', default='').strip()
app.config['STARTUP_PORT'] = get_int_env('PORT', 'RUN_PORT', default=8900)
app.config['STARTUP_DEBUG'] = get_bool_env('DEBUG', 'FLASK_DEBUG', default=False)

# 默认启用文件类型校验；如果需要允许所有文件类型上传，可以将下面的值设置为 True
app.config['ALLOW_ALL_FILE_TYPES'] = True

# 目录列表默认忽略的文件名
app.config['IGNORED_LISTING_NAMES'] = {'.DS_Store'}

# 允许的文件扩展名，可自行修改
ALLOWED_EXTENSIONS = {'jpg', 'png', 'gif', 'mp4', 'zip', 'pdf', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'dump', 'dat'}


def password_is_required():
    return bool((app.config.get('ACCESS_PASSWORD') or '').strip())


def is_authenticated():
    if not password_is_required():
        return True
    return session.get('upload_server_authenticated') is True


def require_authentication(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not is_authenticated():
            return jsonify({'status': 0, 'message': '需要先验证密码'}), 401
        return view_func(*args, **kwargs)

    return wrapped_view

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


def get_unique_filename(filename, directory):
    """
    当同名文件已存在时，自动追加序号，避免覆盖已有文件。
    例如: file.txt -> file_1.txt -> file_2.txt
    """
    base_name, ext = os.path.splitext(filename)
    candidate = filename
    index = 1

    while os.path.exists(os.path.join(directory, candidate)):
        candidate = f"{base_name}_{index}{ext}"
        index += 1

    return candidate


def normalize_relative_path(raw_path):
    """
    将用户传入的相对路径规范化，并阻止目录穿越。
    """
    path = (raw_path or '').strip().replace('\\', '/')
    path = path.lstrip('/')
    normalized = os.path.normpath(path)

    if normalized in ('.', ''):
        return ''

    if normalized.startswith('..') or os.path.isabs(normalized):
        raise ValueError('非法路径')

    return normalized


def build_absolute_path(relative_path):
    """
    根据相对路径构建 uploads 根目录内的绝对路径。
    """
    safe_relative_path = normalize_relative_path(relative_path)
    absolute_path = os.path.join(UPLOAD_FOLDER, safe_relative_path)

    if not os.path.commonpath([os.path.realpath(absolute_path), os.path.realpath(UPLOAD_FOLDER)]) == os.path.realpath(UPLOAD_FOLDER):
        raise ValueError('非法路径')

    return safe_relative_path, absolute_path


def get_request_value(key, default=''):
    """
    同时兼容 JSON 与 form 参数读取。
    """
    data = request.get_json(silent=True)
    if isinstance(data, dict) and key in data:
        return data.get(key, default)
    return request.form.get(key, default)

@app.route('/')
def index():
    return render_template(
        'index.html',
        password_required=password_is_required(),
        authenticated=is_authenticated(),
    )


@app.route('/api/login', methods=['POST'])
def login():
    if not password_is_required():
        session['upload_server_authenticated'] = True
        return jsonify({'status': 1, 'message': '当前未启用密码', 'authenticated': True})

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = request.form

    submitted_password = payload.get('password', '')
    access_password = app.config.get('ACCESS_PASSWORD', '')

    if hmac.compare_digest(str(submitted_password), str(access_password)):
        session['upload_server_authenticated'] = True
        return jsonify({'status': 1, 'message': '验证成功', 'authenticated': True})

    session.pop('upload_server_authenticated', None)
    return jsonify({'status': 0, 'message': '密码错误', 'authenticated': False}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('upload_server_authenticated', None)
    return jsonify({'status': 1, 'message': '已退出登录', 'authenticated': False})

@app.route('/upload', methods=['POST'])
@require_authentication
def upload_file():
    try:
        current_path, target_dir = build_absolute_path(request.form.get('current_path', ''))
    except ValueError:
        return jsonify({'status': 0, 'message': '目标目录非法', 'results': []}), 400

    os.makedirs(target_dir, exist_ok=True)

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
        filename = get_unique_filename(safe_name, target_dir)
        save_path = os.path.join(target_dir, filename)
        file.save(save_path)
        relative_file_path = os.path.join(current_path, filename).replace('\\', '/') if current_path else filename
        file_url = f"/uploads/{quote(relative_file_path, safe='/')}"

        results.append({
            'status': 1,
            'message': '上传成功',
            'url': file_url,
            'filename': filename,
            'original_filename': original_filename,
            'relative_path': relative_file_path,
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
        'current_path': current_path,
        'results': results,
    })


@app.route('/api/list', methods=['GET'])
@require_authentication
def list_files():
    try:
        current_path, current_dir = build_absolute_path(request.args.get('path', ''))
    except ValueError:
        return jsonify({'status': 0, 'message': '目录路径非法'}), 400

    if not os.path.isdir(current_dir):
        return jsonify({'status': 0, 'message': '目录不存在'}), 404

    entries = []
    ignored_names = set(app.config.get('IGNORED_LISTING_NAMES', set()))
    show_ignored = request.args.get('show_ignored', '0') == '1'

    with os.scandir(current_dir) as scanner:
        for item in scanner:
            if not show_ignored and item.name in ignored_names:
                continue

            item_relative_path = os.path.join(current_path, item.name).replace('\\', '/') if current_path else item.name
            stat = item.stat()

            entry = {
                'name': item.name,
                'relative_path': item_relative_path,
                'is_dir': item.is_dir(),
                'size': stat.st_size if item.is_file() else None,
                'modified_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'download_url': None,
            }

            if item.is_file():
                entry['download_url'] = f"/uploads/{quote(item_relative_path, safe='/')}"

            entries.append(entry)

    entries.sort(key=lambda e: (not e['is_dir'], e['name'].lower()))
    parent_path = os.path.dirname(current_path).replace('\\', '/') if current_path else ''

    return jsonify({
        'status': 1,
        'current_path': current_path,
        'parent_path': parent_path if current_path else None,
        'show_ignored': show_ignored,
        'entries': entries,
    })


@app.route('/api/mkdir', methods=['POST'])
@require_authentication
def create_folder():
    folder_name = safe_filename(get_request_value('folder_name', '').strip())
    if not folder_name:
        return jsonify({'status': 0, 'message': '目录名不能为空'}), 400

    try:
        current_path, current_dir = build_absolute_path(get_request_value('current_path', ''))
    except ValueError:
        return jsonify({'status': 0, 'message': '目标目录非法'}), 400

    target_path = os.path.join(current_dir, folder_name)
    if os.path.exists(target_path):
        return jsonify({'status': 0, 'message': '目录已存在'}), 409

    os.makedirs(target_path, exist_ok=False)
    relative_path = os.path.join(current_path, folder_name).replace('\\', '/') if current_path else folder_name

    return jsonify({
        'status': 1,
        'message': '目录创建成功',
        'relative_path': relative_path,
    })


@app.route('/api/delete', methods=['POST'])
@require_authentication
def delete_entry():
    try:
        target_relative_path, target_path = build_absolute_path(get_request_value('target_path', ''))
    except ValueError:
        return jsonify({'status': 0, 'message': '目标路径非法'}), 400

    if not target_relative_path:
        return jsonify({'status': 0, 'message': '不允许删除根目录'}), 400

    if not os.path.exists(target_path):
        return jsonify({'status': 0, 'message': '目标不存在'}), 404

    if os.path.isdir(target_path):
        shutil.rmtree(target_path)
        entry_type = '目录'
    else:
        os.remove(target_path)
        entry_type = '文件'

    return jsonify({
        'status': 1,
        'message': f'{entry_type}删除成功',
        'target_path': target_relative_path,
    })

# 提供静态访问（访问上传后的文件）
@app.route('/uploads/<path:filename>')
@require_authentication
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    startup_mode = app.config.get('STARTUP_MODE', 'lan')
    startup_host = app.config.get('STARTUP_HOST') or (
        '127.0.0.1' if startup_mode == 'local' else '0.0.0.0'
    )
    startup_port = app.config.get('STARTUP_PORT', 8900)
    startup_debug = app.config.get('STARTUP_DEBUG', False)

    if startup_host == '0.0.0.0':
        print(f'File upload server started: http://<LAN-IP>:{startup_port}')
    else:
        print(f'File upload server started: http://127.0.0.1:{startup_port}')

    app.run(host=startup_host, port=startup_port, debug=startup_debug)
