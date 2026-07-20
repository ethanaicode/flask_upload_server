# 局域网上传文件服务

基于 Flask 的简单文件上传服务器，适合在局域网内快速搭建文件上传服务。

## 配置

项目启动时会优先读取同目录或当前工作目录下的 `.env` 文件。建议至少配置以下键：

```env
UPLOAD_FOLDER=/absolute/path/to/uploads
ACCESS_PASSWORD=your_password
SECRET_KEY=replace_with_a_random_secret
STARTUP_MODE=lan
```

- `UPLOAD_FOLDER`：上传目录。可填绝对路径，也可填相对项目目录的路径。
- `ACCESS_PASSWORD`：页面访问密码。留空或不设置时，不启用登录验证。
- `SECRET_KEY`：Flask 会话密钥，启用密码验证时建议设置。
- `STARTUP_MODE`：启动模式。设置为 `lan` 时监听 `0.0.0.0`，设置为 `local` 时监听 `127.0.0.1`。

如果你希望手动指定地址，也可以使用 `HOST` 和 `PORT` 覆盖默认值。

如果同时存在环境变量和 `.env` 文件，程序会优先使用 `.env` 中的值。