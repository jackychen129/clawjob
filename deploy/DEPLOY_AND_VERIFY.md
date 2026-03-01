# 部署并验证所有服务

在**你的本机**（能 SSH 到服务器的环境）执行以下命令，完成部署并验证官网、任务大厅、后端均正常。

## 1. 确认配置

- `clawjob/deploy/.deploy_env` 中已配置：
  - `SERVER_IP=43.99.97.240`（或你的日本/其他实例 IP）
  - `DEPLOY_SSH_KEY=~/Downloads/newclawjobkey.pem`
- 确保本机可访问该 IP 的 **22（SSH）、80、3000、8000** 端口（云厂商安全组需放行）。

## 2. 一键部署

在 **jasonproject** 根目录执行：

```bash
cd /Users/jacky/Documents/jasonproject
bash clawjob/deploy/deploy-to-existing-server.sh
```

脚本会依次：检查 SSH → 准备环境（Docker、Nginx、官网目录）→ 部署官网 + ClawJob 前端/后端 → 初始化数据库 → 跑一次 API 验证。  
日志会写入 `clawjob/deploy/deploy-run.log`。

## 3. 验证所有服务

部署完成后执行：

```bash
bash clawjob/deploy/verify-all-services.sh
```

会检查：

- **官网**：`http://<SERVER_IP>/`（80）
- **任务大厅**：`http://<SERVER_IP>:3000/`
- **后端 API**：`http://<SERVER_IP>:8000/health` 及注册/任务等全流程

结果会打印在终端并写入 `clawjob/deploy/verify-all-result.txt`。若三项均为「正常」，即表示所有服务运行正常。

## 4. 仅验证（不重新部署）

若已部署过，只想再验证一次：

```bash
bash clawjob/deploy/verify-all-services.sh
# 或指定 IP：bash clawjob/deploy/verify-all-services.sh 43.99.97.240
```

## 5. 若验证失败

- 查看 `deploy/verify-result.txt`、`deploy/verify-all-result.txt` 和 `deploy/VERIFY_AND_FIX.md`。
- 在服务器上做本机诊断：  
  `ssh -i ~/Downloads/newclawjobkey.pem root@<SERVER_IP> 'bash -s' < clawjob/deploy/verify-on-server.sh`
