# 放行 22 端口（解决 SSH 连接超时）

部署时若报 `Connection to 43.99.97.240 port 22 timed out`，说明本机连不上服务器的 22 端口，需要在阿里云控制台为轻量应用服务器放行 22 端口。

---

## 方式一：控制台手动放行（约 1 分钟）

1. 打开 **阿里云轻量应用服务器控制台**  
   https://swas.console.aliyun.com/

2. 在实例列表中找到 **公网 IP 为 43.99.97.240** 的实例，点击 **实例 ID** 进入详情。

3. 左侧或顶部切换到 **「防火墙」** 页签。

4. 点击 **「添加规则」**。

5. 填写：
   - **应用类型**：自定义
   - **协议**：TCP
   - **端口**：22（或端口范围 22/22）
   - **来源**：0.0.0.0/0（允许所有 IP 访问，若需限制可填你的公网 IP）
   - **备注**：SSH

6. 点击 **「确定」**。规则即时生效，无需重启。

7. 在本机重试：
   ```bash
   ./clawjob/deploy/check-ssh.sh
   ./clawjob/deploy/deploy-with-cursor-pem.sh
   ```

---

## 方式二：用 API 脚本放行（需 AccessKey）

若已配置阿里云 AccessKey，可用脚本自动添加规则：

```bash
cd /path/to/clawjob

# 安装依赖（仅首次）
pip install aliyun-python-sdk-swas-open aliyun-python-sdk-core

# 按公网 IP 自动查找实例并放行 22（需该账号下能查到该实例）
export ALIBABA_CLOUD_ACCESS_KEY_ID=你的AccessKeyId
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=你的AccessKeySecret
python3 deploy/aliyun_open_port22_swas.py --public-ip 43.99.97.240

# 或已知实例 ID 和地域时
python3 deploy/aliyun_open_port22_swas.py --instance-id i-xxxxx --region-id cn-hangzhou
```

AccessKey 可在阿里云控制台 **AccessKey 管理** 中创建（建议使用 RAM 子账号并仅授予轻量应用服务器相关权限）。

---

## 说明

- **轻量应用服务器** 默认通常已放行 22、80、443；若你之前改过规则或使用自定义镜像，可能 22 被关闭，按上面步骤打开即可。
- 若是 **ECS** 而非轻量，需在 **ECS 控制台 → 安全组** 中添加入方向规则：TCP 22，来源 0.0.0.0/0。
