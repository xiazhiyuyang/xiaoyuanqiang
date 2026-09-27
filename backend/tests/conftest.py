"""测试公共夹具。

只放真正共享的东西。本项目当前测试以纯单元测试为主
（安全工具、敏感词引擎、热度分、权限矩阵、限流），
不依赖数据库与网络，因此不需要起 ASGI 应用——跑得快、失败信息也直接。

后续要加接口级测试时，在这里补 in-memory SQLite 引擎与
`get_db` 依赖覆盖即可，不要在各测试文件里各写一套。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# 测试专用配置：必须在 import app.* 之前设置，否则 Settings 会读到生产 .env
os.environ.setdefault("DEBUG", "False")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only-32bytes")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")   # 强制走进程内降级路径，测试不依赖 Redis
os.environ.setdefault("CORS_ORIGINS", "")


@pytest.fixture
def anyio_backend():
    return "asyncio"
