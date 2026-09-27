"""baseline：现有库结构快照

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-21

这是引入 Alembic 时的「基线」版本，对应 2026-09-21 之前由
`Base.metadata.create_all` 建出来的全部 17 张表。

为什么用 `create_all(checkfirst=True)` 而不是逐表手写 DDL：
- 基线的唯一职责是「让 Alembic 认识现有结构」，不是描述一次真实变更；
- 手写 17 张表的 DDL 极易与模型漂移，而漂移的基线比没有基线更危险；
- `checkfirst=True` 保证对已存在表不做任何操作，因此本迁移对
  **已有生产库是幂等且无副作用的**（实际部署时用 `alembic stamp 0001_baseline`
  直接打标，不会真的执行）。

新库（空库）执行 `alembic upgrade head` 时，本迁移会真正建出全部表。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.database import Base
    import app.models  # noqa: F401  确保所有模型已注册到 metadata

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    # 基线不提供降级：删库不是「回滚」，是事故。
    # 真要回退请用 deploy/backup_campus_db.sh 的备份恢复。
    raise RuntimeError("基线版本不支持 downgrade，请从备份恢复")
