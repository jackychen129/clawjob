#!/usr/bin/env python3
"""
执行 deploy/migrations/*.sql，使本地数据库与模型一致。
用法: PYTHONPATH=. python3 scripts/run_migrations.py
"""
import os
import sys

# 项目根为 backend
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from app.database.relational_db import engine
from sqlalchemy import text

MIGRATIONS_DIR = os.path.join(backend_dir, "..", "deploy", "migrations")

def run_sql_file(filepath: str) -> None:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # 按分号拆分，去掉注释和空语句
    statements = []
    for part in content.split(";"):
        part = part.strip()
        if not part or part.startswith("--"):
            continue
        # 去掉行内注释（简单处理）
        lines = []
        for line in part.split("\n"):
            if "--" in line:
                line = line[: line.index("--")].strip()
            if line:
                lines.append(line)
        if lines:
            statements.append("\n".join(lines))
    with engine.begin() as conn:
        for stmt in statements:
            if not stmt.strip():
                continue
            try:
                conn.execute(text(stmt))
            except Exception as e:
                # IF NOT EXISTS 可能仍会报错（如列已存在），视情况忽略
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    continue
                raise

def main():
    if not os.path.isdir(MIGRATIONS_DIR):
        print("Migrations dir not found:", MIGRATIONS_DIR)
        return 1
    for name in sorted(os.listdir(MIGRATIONS_DIR)):
        if not name.endswith(".sql"):
            continue
        path = os.path.join(MIGRATIONS_DIR, name)
        print("Running", name, "...")
        try:
            run_sql_file(path)
            print("  OK")
        except Exception as e:
            print("  FAIL:", e)
            return 1
    print("All migrations done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
