# 测试通过后更新线上

1. **本地一键**（与 CI 建议一致）  
   ```bash
   ./deploy/run-tests-and-verify.sh
   ```  
   包含：`pytest tests/test_clawjob_api.py`、`npm run test:run`、`npm run build`。

2. **仅线上 API 冒烟**（需可访问的 API/前端）  
   ```bash
   export CLAWJOB_API_URL=http://你的服务器:8000
   export CLAWJOB_FRONTEND_URL=http://你的服务器:3000   # 可选
   python3 deploy/verify-online-e2e.py
   ```

3. **部署到已有服务器**（需本机 `deploy/.deploy_env` 或环境变量 `SERVER_IP`、SSH）  
   ```bash
   cd /path/to/clawjob
   SERVER_IP=你的公网IP ./deploy/deploy-to-server.sh
   ```  
   详见 [DEPLOY_QUICK.md](../deploy/DEPLOY_QUICK.md)。

4. **推送到 GitHub**  
   ```bash
   git push origin main
   ```

> 线上部署依赖你的 SSH 密钥与服务器；本仓库脚本无法在无权访问的机器上代为执行。
