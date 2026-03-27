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
ALLOWED_EXTENSIONS = {'jpg', 'png', 'gif', 'mp4', 'zip', 'pdf', 'txt', 'docx', 'xlsx', 'dump', 'dat'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>文件上传服务</title>
        <style>
            :root {
                color-scheme: light;
                --bg: linear-gradient(135deg, #f4efe6 0%, #dbe7f3 100%);
                --card: rgba(255, 252, 247, 0.92);
                --border: rgba(45, 76, 99, 0.16);
                --text: #1f2a33;
                --muted: #5f6f7b;
                --accent: #166534;
                --accent-strong: #14532d;
                --danger: #b42318;
                --danger-soft: #fef3f2;
                --success-soft: #ecfdf3;
                --shadow: 0 18px 50px rgba(31, 42, 51, 0.12);
            }

            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
                color: var(--text);
                background: var(--bg);
                min-height: 100vh;
            }

            .page {
                width: min(960px, calc(100vw - 32px));
                margin: 40px auto;
                display: grid;
                gap: 20px;
            }

            .hero,
            .results {
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 24px;
                box-shadow: var(--shadow);
                backdrop-filter: blur(10px);
            }

            .hero {
                padding: 28px;
            }

            .hero h2,
            .results h3 {
                margin: 0;
                font-weight: 700;
            }

            .hero p {
                margin: 12px 0 0;
                color: var(--muted);
                line-height: 1.6;
            }

            form {
                margin-top: 24px;
                display: grid;
                gap: 16px;
            }

            .upload-box {
                border: 1.5px dashed rgba(22, 101, 52, 0.28);
                border-radius: 18px;
                padding: 20px;
                background: rgba(255, 255, 255, 0.65);
            }

            input[type="file"] {
                width: 100%;
                color: var(--muted);
            }

            .actions {
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }

            button {
                border: none;
                border-radius: 999px;
                padding: 12px 22px;
                font-size: 15px;
                font-weight: 700;
                color: #fff;
                background: linear-gradient(135deg, var(--accent) 0%, var(--accent-strong) 100%);
                cursor: pointer;
                transition: transform 0.18s ease, opacity 0.18s ease;
            }

            button:hover {
                transform: translateY(-1px);
            }

            button:disabled {
                opacity: 0.65;
                cursor: wait;
                transform: none;
            }

            .hint,
            .status-text {
                color: var(--muted);
                font-size: 14px;
            }

            .results {
                padding: 24px;
            }

            .results-head {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
                margin-bottom: 16px;
            }

            .empty-state {
                padding: 24px;
                text-align: center;
                color: var(--muted);
                border: 1px dashed var(--border);
                border-radius: 18px;
                background: rgba(255, 255, 255, 0.55);
            }

            .table-wrap {
                overflow-x: auto;
                border: 1px solid rgba(45, 76, 99, 0.1);
                border-radius: 18px;
                background: rgba(255, 255, 255, 0.72);
            }

            table {
                width: 100%;
                border-collapse: collapse;
                min-width: 680px;
            }

            th,
            td {
                padding: 14px 16px;
                border-bottom: 1px solid rgba(45, 76, 99, 0.08);
                text-align: left;
                vertical-align: top;
            }

            th {
                font-size: 13px;
                letter-spacing: 0.02em;
                color: var(--muted);
                background: rgba(219, 231, 243, 0.42);
            }

            tr:last-child td {
                border-bottom: none;
            }

            .badge {
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: 700;
            }

            .badge.success {
                color: var(--accent-strong);
                background: var(--success-soft);
            }

            .badge.error {
                color: var(--danger);
                background: var(--danger-soft);
            }

            a {
                color: var(--accent-strong);
            }

            @media (max-width: 720px) {
                .page {
                    width: calc(100vw - 20px);
                    margin: 20px auto;
                }

                .hero,
                .results {
                    border-radius: 20px;
                    padding: 20px;
                }

                th,
                td {
                    padding: 12px;
                }
            }
        </style>
    </head>
    <body>
        <main class="page">
            <section class="hero">
                <h2>文件上传测试</h2>
                <p>上传时保持在当前页面，服务端返回的 JSON 会被解析后展示在下方结果列表中。</p>

                <form id="upload-form" enctype="multipart/form-data">
                    <div class="upload-box">
                        <input id="file-input" type="file" name="file" required>
                    </div>
                    <div class="actions">
                        <button id="submit-button" type="submit">上传</button>
                        <span id="status-text" class="status-text">等待选择文件</span>
                    </div>
                    <div class="hint">支持多次上传，新的结果会持续追加到页面中。</div>
                </form>
            </section>

            <section class="results">
                <div class="results-head">
                    <h3>上传结果</h3>
                    <span class="hint">展示本次页面会话中的上传记录</span>
                </div>

                <div id="empty-state" class="empty-state">暂无上传记录，上传后会在这里追加结果。</div>

                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>时间</th>
                                <th>上传文件</th>
                                <th>结果</th>
                                <th>说明</th>
                                <th>访问地址</th>
                            </tr>
                        </thead>
                        <tbody id="result-body"></tbody>
                    </table>
                </div>
            </section>
        </main>

        <script>
            const form = document.getElementById('upload-form');
            const fileInput = document.getElementById('file-input');
            const submitButton = document.getElementById('submit-button');
            const statusText = document.getElementById('status-text');
            const resultBody = document.getElementById('result-body');
            const emptyState = document.getElementById('empty-state');

            function escapeHtml(value) {
                return String(value).replace(/[&<>\"']/g, function(char) {
                    const entityMap = {
                        '&': '&amp;',
                        '<': '&lt;',
                        '>': '&gt;',
                        '\"': '&quot;',
                        "'": '&#39;'
                    };
                    return entityMap[char] || char;
                });
            }

            function appendResultRow(record) {
                emptyState.style.display = 'none';

                const statusClass = record.ok ? 'success' : 'error';
                const statusLabel = record.ok ? '成功' : '失败';
                const fileLink = record.url
                    ? `<a href="${escapeHtml(record.url)}" target="_blank" rel="noreferrer">查看文件</a>`
                    : '-';

                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${escapeHtml(record.time)}</td>
                    <td>${escapeHtml(record.filename)}</td>
                    <td><span class="badge ${statusClass}">${statusLabel}</span></td>
                    <td>${escapeHtml(record.message)}</td>
                    <td>${fileLink}</td>
                `;

                resultBody.prepend(row);
            }

            form.addEventListener('submit', async function(event) {
                event.preventDefault();

                const selectedFile = fileInput.files[0];
                if (!selectedFile) {
                    statusText.textContent = '请先选择文件';
                    appendResultRow({
                        time: new Date().toLocaleString('zh-CN'),
                        filename: '未选择文件',
                        ok: false,
                        message: '提交前没有选择文件',
                        url: ''
                    });
                    return;
                }

                const formData = new FormData();
                formData.append('file', selectedFile);

                submitButton.disabled = true;
                statusText.textContent = `正在上传 ${selectedFile.name}...`;

                try {
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });

                    const payload = await response.json();
                    const ok = response.ok && payload.status === 1;

                    appendResultRow({
                        time: new Date().toLocaleString('zh-CN'),
                        filename: payload.original_filename || selectedFile.name,
                        ok,
                        message: payload.message || '上传完成',
                        url: ok ? payload.url || '' : ''
                    });

                    statusText.textContent = ok ? `上传完成：${selectedFile.name}` : `上传失败：${selectedFile.name}`;

                    if (ok) {
                        form.reset();
                    }
                } catch (error) {
                    appendResultRow({
                        time: new Date().toLocaleString('zh-CN'),
                        filename: selectedFile.name,
                        ok: false,
                        message: '请求失败，请检查服务状态或返回内容是否为 JSON',
                        url: ''
                    });
                    statusText.textContent = `请求失败：${selectedFile.name}`;
                } finally {
                    submitButton.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    '''

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 0, 'message': '没有文件部分'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 0, 'message': '未选择文件'})

    if file and allowed_file(file.filename):
        original_filename = file.filename
        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        file_url = f"/uploads/{filename}"
        return jsonify({
            'status': 1,
            'message': '上传成功',
            'url': file_url,
            'filename': filename,
            'original_filename': original_filename,
        })

    return jsonify({'status': 0, 'message': '文件类型不允许'})

# 提供静态访问（访问上传后的文件）
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    # 在局域网可访问
    print("🚀 文件上传服务启动中：请访问 http://<本机局域网IP>:8900")
    app.run(host='0.0.0.0', port=8900, debug=True)
