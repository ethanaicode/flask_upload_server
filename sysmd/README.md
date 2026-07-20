# systemd deployment notes

This folder provides a minimal systemd setup for this project.

Files
- flask_upload_server.service: systemd unit file template.

Before use
1. Update WorkingDirectory in flask_upload_server.service.
2. Update ExecStart in flask_upload_server.service.
3. Update User and Group if your service user is not www-data.

Suggested .env for local-only backend behind nginx
- STARTUP_MODE=local
- PORT=8900
- DEBUG=0

Install steps on Linux server
1. Copy service file to systemd:
   sudo cp flask_upload_server.service /etc/systemd/system/flask_upload_server.service
2. Reload systemd:
   sudo systemctl daemon-reload
3. Enable auto-start on boot:
   sudo systemctl enable flask_upload_server
4. Start now:
   sudo systemctl start flask_upload_server
5. Check status:
   sudo systemctl status flask_upload_server
6. View logs:
   sudo journalctl -u flask_upload_server -f

Update workflow after code changes
1. Deploy new code.
2. Restart service:
   sudo systemctl restart flask_upload_server
3. Verify status and logs.

Nginx reverse proxy recommendation
- Keep Python service bound to 127.0.0.1.
- Let nginx expose 80/443 and proxy to 127.0.0.1:8900.
