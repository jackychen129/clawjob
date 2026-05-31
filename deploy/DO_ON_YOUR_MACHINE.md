# 在本机执行（部署 + 验证并修复）

Cursor 当前环境无法访问你的服务器 `43.99.97.240`，部署与验证需要在你本机执行。

## 一条命令做完：部署 + 验证直到通过

在**能 SSH 到 43.99.97.240** 的电脑上打开终端，执行：

```bash
cd /Users/jacky/Documents/jasonproject/clawjob
chmod +x deploy/run-deploy-and-verify.sh deploy/verify-and-fix-until-pass.sh
./deploy/run-deploy-and-verify.sh
```

脚本会依次：

1. **部署**：构建官网并上传、同步 ClawJob 代码、在服务器上启动 Docker、初始化数据库。
2. **验证并修复**：请求线上 API 做检查；若超时则 SSH 启动/构建容器，若 500 则执行 init_db，若 CORS 则配置并重启，然后重试，最多 5 轮，直到 **「所有检查已通过」**。

## 只做验证并修复（已部署过）

若已经部署过，只需验证并自动修到通过：

```bash
cd /Users/jacky/Documents/jasonproject/clawjob
./deploy/verify-and-fix-until-pass.sh
```

## 前置条件

- 本机已配置好认证（二选一）：
  - **密钥**：`deploy/.deploy_env` 中 `DEPLOY_SSH_KEY=~/Downloads/cursor.pem`（或你的密钥路径），且公钥已在服务器 `authorized_keys`。
  - **密码**：`export DEPLOY_SSH_PASSWORD='你的root密码'`，且已安装 `sshpass`（`brew install sshpass`）。
- 服务器防火墙/安全组已放行：22（SSH）、80、3000、8000。

执行完成后，若出现 **「========== 所有检查已通过 ==========」** 即表示部署与验证都已完成。
