# Deploy

本目录包含 Docker Compose 配置与部署脚本，供**运维/自托管**使用。应用开发与贡献请从仓库根目录 [README.md](../README.md) 开始。

| 文件 | 用途 |
|------|------|
| [docker-compose.yml](docker-compose.yml) | 本地/开发全栈 |
| [docker-compose.prod.yml](docker-compose.prod.yml) | 生产 Compose |
| [DEPLOY_ALIYUN.md](DEPLOY_ALIYUN.md) | 阿里云 ECS 部署说明 |
| [deploy-all.sh](deploy-all.sh) | 一键同步并重启（需配置 `.deploy_env`） |
| [../.env.example](../.env.example) | 环境变量示例 |
| [.deploy_env.example](.deploy_env.example) | 部署 SSH/域名配置示例 |

生产环境务必修改默认密码、`JWT_SECRET` 与 `CORS_ORIGINS`。
