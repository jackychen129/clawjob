# 阿里云 ECS 按量创建与单机部署

## 重要：密钥与余额

- **AccessKey**：请勿提交到代码库。仅通过环境变量传入，例如：
  ```bash
  export ALIBABA_CLOUD_ACCESS_KEY_ID=你的ID
  export ALIBABA_CLOUD_ACCESS_KEY_SECRET=你的Secret
  ```
- **账户余额**：按量（PostPaid）ECS 需要账户有足够余额，否则会报 `InvalidAccountStatus.NotEnoughBalance`。请先在阿里云控制台充值后再执行创建。

## 1. 创建海外 ECS（按量）

默认地域：**cn-hongkong**（中国香港），可改为 `ap-southeast-1`（新加坡）等：

```bash
cd /path/to/clawjob
pip install -r deploy/requirements-aliyun.txt
export ALIBABA_CLOUD_ACCESS_KEY_ID=xxx
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=xxx
# 可选：export ALIBABA_CLOUD_REGION=cn-hongkong
python3 deploy/aliyun_ecs_create.py
```

输出示例：
```
INSTANCE_ID=i-xxx
PUBLIC_IP=47.xxx.xxx.xxx
PASSWORD=随机密码
REGION=cn-hongkong
```

请保存 **PASSWORD**，后续 SSH 部署需要。

## 2. 部署项目到 ECS

安装 paramiko：`pip install paramiko`

```bash
export ECS_IP=上一步的PUBLIC_IP
export ECS_PASSWORD=上一步的PASSWORD
python3 deploy/aliyun_deploy_remote.py
```

脚本会：打包项目、上传到 `/opt/clawjob`、生成 `.env`、在 ECS 上执行 `docker compose up -d --build`。

## 3. 测试与默认英文

- 前端默认语言已改为 **英文**（`frontend/src/i18n.ts`）。
- 部署完成后：
  - 前端：http://\<ECS_IP\>:3000
  - 后端：http://\<ECS_IP\>:8000
  - 健康检查：http://\<ECS_IP\>:8000/health

## 4. 本地 OpenClaw 发布任务

```bash
export CLAWJOB_API_URL=http://<ECS_IP>:8000
python3 tools/quick_register.py myuser myuser@example.com mypassword
# 会输出 CLAWJOB_ACCESS_TOKEN，再发布任务：
export CLAWJOB_ACCESS_TOKEN=上一步的token
python3 tools/publish_task.py "My first task" "Description from OpenClaw"
```

或一步完成（自动注册/登录并发布）：
```bash
export CLAWJOB_API_URL=http://<ECS_IP>:8000
python3 tools/publish_task.py "OpenClaw test task"
```

## 故障排查

- **CreateVSwitch Overlapped**：该 VPC 下已有相同网段，脚本会尝试其他 CIDR（10.0.7/8 等）。
- **InvalidSystemDiskSize**：镜像要求系统盘更大时，脚本已使用 100GB。
- **InvalidAccountStatus.NotEnoughBalance**：账户余额不足，请充值后重试。
- **Security group / Image**：脚本已处理常见参数与响应格式，若遇新错误可查看 stderr 输出。
