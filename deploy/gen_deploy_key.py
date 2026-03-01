#!/usr/bin/env python3
"""生成 deploy/.ssh 下的 Ed25519 密钥，并输出「在服务器执行一次」的一行命令。"""
import os
import sys

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("请先安装: pip install cryptography", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_DIR = os.path.join(SCRIPT_DIR, ".ssh")
PRIV = os.path.join(KEY_DIR, "id_ed25519")
PUB = os.path.join(KEY_DIR, "id_ed25519.pub")

os.makedirs(KEY_DIR, mode=0o700, exist_ok=True)

if os.path.exists(PRIV):
    with open(PRIV, "rb") as f:
        priv_content = f.read()
    with open(PUB, "r") as f:
        pub_line = f.read().strip()
else:
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    )
    with open(PRIV, "wb") as f:
        f.write(priv_bytes)
    os.chmod(PRIV, 0o600)
    pub_line = pub_bytes.decode("utf-8").strip()
    with open(PUB, "w") as f:
        f.write(pub_line + "\n")
    os.chmod(PUB, 0o644)

# 一行命令：在服务器上追加公钥（复制整行到服务器终端执行）
one_liner = f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '{pub_line}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

run_once_file = os.path.join(SCRIPT_DIR, "run-on-server-once.txt")
with open(run_once_file, "w") as f:
    f.write("# 用阿里云轻量控制台或 ssh root@43.99.97.240 登录服务器后，复制下面一行执行：\n\n")
    f.write(one_liner + "\n")

print("已生成 deploy/.ssh/id_ed25519 并写入 run-on-server-once.txt")
print("请在服务器上执行 run-on-server-once.txt 中的那一行，然后运行: ./deploy/deploy-all.sh")
print("\n--- 在服务器执行这一行 ---\n")
print(one_liner)
