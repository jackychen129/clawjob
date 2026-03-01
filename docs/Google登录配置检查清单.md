# Google 登录配置检查清单

按下列项逐条核对，可快速排查「Sign in with Google」不工作的问题。

---

## 一、自动检查（推荐）

后端**已启动**时，在项目根目录执行：

```bash
python3 tools/check_google_oauth.py
```

若指定线上 API 地址：

```bash
CLAWJOB_API_URL=https://api.你的域名.com python3 tools/check_google_oauth.py
```

脚本会输出：当前是否已配置、`redirect_uri` / `frontend_url` 的值，以及 Google Console 需核对项。

---

## 二、后端环境变量

在后端运行环境中（如 `backend/.env` 或部署环境变量）确认：

| 变量 | 说明 | 示例 |
|------|------|------|
| `GOOGLE_CLIENT_ID` | Google OAuth 客户端 ID | 从 Console 复制 |
| `GOOGLE_CLIENT_SECRET` | Google OAuth 客户端密钥 | 从 Console 复制 |
| `GOOGLE_REDIRECT_URI` | **后端**回调地址，必须与 Console 中「授权重定向 URI」**完全一致** | 本地: `http://localhost:8000/auth/google/callback`<br>线上: `https://api.你的域名.com/auth/google/callback` |
| `FRONTEND_URL` | **前端** SPA 完整访问地址（登录成功后跳转到这里） | 本地: `http://localhost:3000`<br>线上: `https://你的前端域名.com`（若前端在子路径则含路径） |

注意：

- `GOOGLE_REDIRECT_URI` 是**后端**的地址，不是前端。
- `FRONTEND_URL` 不要以 `/` 结尾；若前端在子路径，例如 `https://example.com/app`，则填完整 URL。

---

## 三、Google Cloud Console

1. 打开 [Google Cloud Console](https://console.cloud.google.com/) → **APIs 与服务** → **凭据**。
2. 创建或编辑 **OAuth 2.0 客户端 ID**，应用类型选择 **「Web 应用」**。
3. **已授权的重定向 URI**：
   - 添加**一条**，与后端环境变量 `GOOGLE_REDIRECT_URI` **一字不差**（含 `http`/`https`、域名、端口、路径）。
   - 例如：`https://api.你的域名.com/auth/google/callback`。
4. **已授权的 JavaScript 来源**（可选但建议）：
   - 添加前端页面的 origin，例如 `https://你的前端域名.com`。
   - 若前端与 API 同域，添加该域即可。

保存后，修改可能需几分钟生效。

---

## 四、常见错误与对应检查

| 现象 | 优先检查 |
|------|----------|
| 点击「使用 Google 登录」后显示「未配置 GOOGLE_CLIENT_ID」或 503 | 后端未设置 `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`，或未重启 |
| 授权后提示 token_exchange / invalid_grant | Console 中「授权重定向 URI」与 `GOOGLE_REDIRECT_URI` 是否**完全一致**（协议、域名、端口、路径） |
| 授权后跳回前端但未登录（或白屏） | `FRONTEND_URL` 是否为用户实际打开前端的地址（含端口、子路径）；前端是否从 `#/auth/callback?token=...` 正确解析 token |
| 登录弹窗里「使用 Google 登录」为灰色 | 后端未配置或 `GET /auth/google/status` 返回 `configured: false`；属预期行为，配置后刷新即可 |

---

## 五、验证通过时

- 点击「使用 Google 登录」→ 跳转 Google 授权页 → 授权后应回到前端并已登录。
- 可再次运行 `python3 tools/check_google_oauth.py`，确认输出为「后端已配置 Google OAuth」并核对 Console 两项。
