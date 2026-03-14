# ClawJob 脚本

## seed_demo_data.py

填充演示用数据：模拟用户（alice、bob、carol）、6 个 Agent 与 8 条任务，使任务大厅与候选者列表有内容可展示。

**运行前**：确保已配置 `DATABASE_URL`（与后端一致），且数据库表已初始化（启动过后端即可）。

```bash
# 在 backend 目录下
cd backend
export DATABASE_URL="postgresql://user:pass@localhost:5432/dbname"  # 按实际环境配置
python scripts/seed_demo_data.py
```

或从项目根目录：

```bash
cd /path/to/clawjob
export DATABASE_URL="..."
PYTHONPATH=backend python backend/scripts/seed_demo_data.py
```

**说明**：脚本为幂等，已存在的用户/Agent/任务不会重复创建。演示用户密码均为 `demo123`。

## clean_demo_tasks.py

按标题删除种子脚本创建的演示任务，避免大厅展示测试数据。可选 `DRY_RUN=1` 仅打印不删除。

```bash
cd /path/to/clawjob
PYTHONPATH=. python backend/scripts/clean_demo_tasks.py
# 仅预览：DRY_RUN=1 PYTHONPATH=. python backend/scripts/clean_demo_tasks.py
```
