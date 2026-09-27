"""posts 增加热度分字段与热门流索引

Revision ID: 0002_post_hot_score
Revises: 0001_baseline
Create Date: 2026-09-21

配合 app/core/hotness.py：热门流从 `ORDER BY like_count` 改为
`ORDER BY hot_score`（带时间衰减），避免老的高赞帖永久霸榜。

字段带 server_default='0'，因此对存量行是安全的即时加列；
存量行的真实分数由部署脚本调用 recompute_recent() 回填（服务启动时也会自动跑一次）。
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_post_hot_score"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "posts"
COLUMN = "hot_score"
INDEX = "idx_posts_status_hot"


def _columns(bind) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(TABLE)}


def _indexes(bind) -> set[str]:
    return {i["name"] for i in sa.inspect(bind).get_indexes(TABLE)}


def upgrade() -> None:
    bind = op.get_bind()
    # 幂等保护：本项目的库可能已被 create_all 建过该列，重复加列会直接报错中断部署
    if COLUMN not in _columns(bind):
        with op.batch_alter_table(TABLE) as batch_op:
            batch_op.add_column(sa.Column(
                COLUMN, sa.Float(), nullable=False, server_default="0",
                comment="热度分，越大越靠前",
            ))
    if INDEX not in _indexes(bind):
        with op.batch_alter_table(TABLE) as batch_op:
            batch_op.create_index(INDEX, ["status", COLUMN])


def downgrade() -> None:
    bind = op.get_bind()
    if INDEX in _indexes(bind):
        with op.batch_alter_table(TABLE) as batch_op:
            batch_op.drop_index(INDEX)
    if COLUMN in _columns(bind):
        with op.batch_alter_table(TABLE) as batch_op:
            batch_op.drop_column(COLUMN)
