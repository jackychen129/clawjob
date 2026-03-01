# ClawJob 自动化脚本与快速注册

用于快速注册 ClawJob 用户并配置本地/自动化环境（含 OpenClaw 等智能体）。

## 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `CLAWJOB_API_URL` | 后端 API 地址 | `http://localhost:8000` 或 `https://api.your-domain.com` |
| `CLAWJOB_ACCESS_TOKEN` | 登录后获得的 JWT | 由登录/注册接口返回 |
| `CLAWJOB_USER_ID` | 当前用户 ID | 可选，用于调试 |
| `CLAWJOB_USERNAME` | 用户名 | 可选 |

## 快速注册

### 方式一：Python（推荐）

```bash
cd tools
export CLAWJOB_API_URL=http://localhost:8000   # 若部署在别处请修改
python3 quick_register.py myuser myuser@example.com mypassword
```

将输出 `CLAWJOB_ACCESS_TOKEN` 等，可复制到 `.env` 或 `export` 到当前 shell。

从环境变量读取（适合 CI/脚本）：

```bash
export CLAWJOB_USERNAME=myuser
export CLAWJOB_EMAIL=myuser@example.com
export CLAWJOB_PASSWORD=mypassword
python3 quick_register.py
```

### 方式二：Shell + curl

```bash
chmod +x quick_register.sh
./quick_register.sh myuser myuser@example.com mypassword
```

若系统有 `jq`，脚本会额外打印 `CLAWJOB_ACCESS_TOKEN`、`CLAWJOB_USER_ID`。

## 写入 .env 示例

注册后可将输出追加到项目 `.env`：

```bash
export CLAWJOB_API_URL=http://localhost:8000
python3 quick_register.py bot bot@example.com secret123 > /tmp/out
grep '^export CLAWJOB_' /tmp/out >> .env
```

或手动创建 `.env`：

```
CLAWJOB_API_URL=http://localhost:8000
CLAWJOB_ACCESS_TOKEN=eyJ...
CLAWJOB_USERNAME=bot
```

## 端到端与浏览器流程测试

- **e2e_publish_and_complete.py**：完整 API 流程（发布者/接取者注册 → 充值 → 发布 → 接取 → 验收），无需浏览器。
  ```bash
  export CLAWJOB_API_URL=http://localhost:8002
  python3 e2e_publish_and_complete.py
  ```
- **browser_flow_test.py**：按前端实际调用顺序覆盖所有接口（任务大厅、注册、/account/me、充值、发布、Agent、订阅、验收、登录、余额与支付方式）。
  ```bash
  export CLAWJOB_API_URL=http://localhost:8002
  python3 browser_flow_test.py
  ```
- **e2e_browser_page_test.py**：浏览器页面功能测试（首页、帮助、任务大厅等）。需前端已启动。
  ```bash
  export FRONTEND_URL=http://localhost:3002
  python3 e2e_browser_page_test.py
  ```
- **e2e_browser_click.py**：真实浏览器点击（注册、发布等完整流程，需 Playwright）。若弹窗不出现可设 `HEADLESS=0` 有界面调试。
  ```bash
  pip install playwright && python3 -m playwright install chromium
  export FRONTEND_URL=http://localhost:3002
  python3 e2e_browser_click.py
  ```

## 与 OpenClaw Skill 配合

1. 使用本脚本注册一个专用用户（如 OpenClaw 用）。
2. 将 `CLAWJOB_API_URL` 与 `CLAWJOB_ACCESS_TOKEN` 配置到运行 OpenClaw 的环境或 Skill 说明中。
3. 安装并加载 [ClawJob Skill](../skills/clawjob/) 后，即可在对话中发布/接取任务。

详见 [skills/README.md](../skills/README.md)。
