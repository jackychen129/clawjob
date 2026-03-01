#!/usr/bin/env python3
"""
通过 SSH 将当前项目部署到已创建的 ECS。需安装 paramiko: pip install paramiko
环境变量: ECS_IP, ECS_PASSWORD（root 密码）, 可选 ECS_SSH_KEY_PATH
或: ECS_IP=1.2.3.4 ECS_PASSWORD=xxx python3 deploy/aliyun_deploy_remote.py
"""
from __future__ import print_function
import os
import sys
import subprocess
import tempfile
import time

def env(key, default=""):
    return os.environ.get(key, default).strip()

def main():
    ip = env("ECS_IP")
    password = env("ECS_PASSWORD")
    key_path = env("ECS_SSH_KEY_PATH")
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if not ip:
        print("Set ECS_IP", file=sys.stderr)
        sys.exit(1)
    if not password and not key_path:
        print("Set ECS_PASSWORD or ECS_SSH_KEY_PATH", file=sys.stderr)
        sys.exit(2)

    try:
        import paramiko
    except ImportError:
        print("pip install paramiko", file=sys.stderr)
        sys.exit(3)

    # 打包
    print("Creating tarball...", file=sys.stderr)
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as f:
        tarball = f.name
    try:
        subprocess.run([
            "tar", "--exclude=node_modules", "--exclude=.git", "--exclude=**/__pycache__",
            "--exclude=frontend/dist", "--exclude=deploy/data", "--exclude=*.pyc",
            "-czvf", tarball, "-C", project_root, ".",
        ], check=True, cwd=project_root, capture_output=True)
    except Exception as e:
        print("tar failed:", e, file=sys.stderr)
        os.unlink(tarball)
        sys.exit(4)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        if key_path:
            client.connect(ip, username="root", key_filename=key_path, timeout=30)
        else:
            client.connect(ip, username="root", password=password, timeout=30)
    except Exception as e:
        print("SSH connect failed:", e, file=sys.stderr)
        os.unlink(tarball)
        sys.exit(5)

    sftp = client.open_sftp()
    remote_tar = "/tmp/clawjob-release.tar.gz"
    print("Uploading tarball...", file=sys.stderr)
    sftp.put(tarball, remote_tar)
    sftp.close()
    os.unlink(tarball)

    api_base = f"http://{ip}:8000"
    frontend_url = f"http://{ip}:3000"
    jwt_secret = os.urandom(32).hex()
    db_pass = os.urandom(16).hex()
    redis_pass = os.urandom(12).hex()

    env_content = f"""VITE_API_BASE_URL={api_base}
FRONTEND_URL={frontend_url}
CORS_ORIGINS={frontend_url}
POSTGRES_PASSWORD={db_pass}
DATABASE_URL=postgresql://agentarena:{db_pass}@postgres:5432/agentarena
REDIS_PASSWORD={redis_pass}
REDIS_URL=redis://:{redis_pass}@redis:6379/0
JWT_SECRET={jwt_secret}
ENV=production
"""

    def run(cmd):
        stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
        out = stdout.read().decode()
        err = stderr.read().decode()
        code = stdout.channel.recv_exit_status()
        return code, out, err

    print("Installing Docker if needed...", file=sys.stderr)
    run("command -v docker >/dev/null 2>&1 || (curl -fsSL https://get.docker.com | sh)")
    run("mkdir -p /opt/clawjob && cd /opt/clawjob && tar -xzf " + remote_tar + " && rm -f " + remote_tar)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write(env_content)
        f.flush()
        local_env = f.name
    try:
        sftp = client.open_sftp()
        sftp.put(local_env, "/opt/clawjob/deploy/.env")
        sftp.close()
    finally:
        os.unlink(local_env)

    print("Running docker compose...", file=sys.stderr)
    code, out, err = run("cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml --env-file .env up -d --build 2>&1")
    print(out or err, file=sys.stderr)
    if code != 0:
        print("Docker compose failed", file=sys.stderr)
        client.close()
        sys.exit(6)

    # 初始化数据库表（recharge_orders 等）
    run("sleep 20 && docker compose -f /opt/clawjob/deploy/docker-compose.prod.yml exec -T backend python3 -c \"from app.database.relational_db import init_db; init_db()\" 2>/dev/null || true")

    print("Deploy done. Frontend: %s  Backend: %s" % (frontend_url, api_base), file=sys.stderr)
    client.close()

if __name__ == "__main__":
    main()
