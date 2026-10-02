"""Add the public first-party quote catalog and owner-scoped daily allocation."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


QUOTES = (
    ("q01", "且以微渺而恒定的努力，对抗盛大而冗长的空虚。"),
    ("q02", "知难上，戒骄狂。常自省，穷途明，事华于今，不溺于往，早登青云。"),
    ("q03", "你知道，你可以改变生活，但必须真心想要改变。"),
    ("q04", "因为我有能力跨越，这个考验才会降临。"),
    ("q05", "待到秋来九月八，我花开后百花杀。"),
    ("q06", "带着爸爸妈妈去研究生学校看看。"),
    ("q07", "国家不缺我一个研究生，但是我家缺。"),
    ("q08", "一颗向上的心脏不能有一副下坠而懒惰的身体。"),
    ("q09", "你既想又何必怕，你既怕又何必想。"),
    ("q10", "远大前程我自己挣。"),
    ("q11", "现在比任何时候都更接近理想目标。"),
    ("q12", "别人能做到，我为什么做不到；别人做不到，关我什么事。"),
    ("q13", "完成大于完美，坚持就是破局。"),
    ("q14", "你知道的，我做什么都会成功。"),
    ("q15", "神明如果不帮你，说明神明相信你。"),
    ("q16", "灵魂是命运的先知。"),
    ("q17", "你的奖励是离开这样的生活。"),
    ("q18", "没关系，再多背一点，可以的。"),
    ("q19", "我想看看一个民办本科的学生能走多远。"),
    ("q20", "我可以苦一阵子，不能苦一辈子。"),
    ("q21", "向外求求而不得，向内求生生不息。"),
    ("q22", "人外有人又如何，我外也有我。"),
    ("q23", "海压竹枝低复举，风吹山角晦还明。"),
)


def upgrade():
    op.create_table(
        "quotes",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("author", sa.Text()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.bulk_insert(
        sa.table(
            "quotes",
            sa.column("id", sa.String(40)),
            sa.column("text", sa.Text()),
            sa.column("author", sa.Text()),
            sa.column("enabled", sa.Boolean()),
            sa.column("content_version", sa.Integer()),
        ),
        [
            {"id": quote_id, "text": text, "author": None, "enabled": True, "content_version": 1}
            for quote_id, text in QUOTES
        ],
    )
    op.create_table(
        "quote_preferences",
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("quote_id", sa.String(40), nullable=False, primary_key=True),
        sa.Column("text_snapshot", sa.Text(), nullable=False),
        sa.Column("favorited", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("disliked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], name="fk_quote_pref_quote"),
        sa.UniqueConstraint("owner_id", "quote_id", name="uq_quote_preference_owner_quote"),
        sa.CheckConstraint("version >= 1", name="ck_quote_preference_version"),
    )
    op.create_index(
        "ix_quote_preference_owner_favorite",
        "quote_preferences",
        ["owner_id", "favorited", "updated_at"],
    )
    op.create_index(
        "ix_quote_preference_owner_disliked",
        "quote_preferences",
        ["owner_id", "disliked", "updated_at"],
    )
    op.create_table(
        "quote_rounds",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "id", name="uq_quote_round_owner_id"),
        sa.UniqueConstraint("owner_id", "round_number", name="uq_quote_round_owner_number"),
        sa.CheckConstraint("round_number >= 1", name="ck_quote_round_number"),
    )
    op.create_index("ix_quote_round_owner", "quote_rounds", ["owner_id", "round_number"])
    op.create_table(
        "quote_round_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("round_id", sa.String(36), nullable=False),
        sa.Column("quote_id", sa.String(40), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["owner_id", "round_id"],
            ["quote_rounds.owner_id", "quote_rounds.id"],
            name="fk_quote_item_round_owner",
        ),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], name="fk_quote_item_quote"),
        sa.UniqueConstraint("round_id", "quote_id", name="uq_quote_round_item"),
        sa.UniqueConstraint("round_id", "position", name="uq_quote_round_position"),
        sa.CheckConstraint("position >= 0", name="ck_quote_round_position"),
    )
    op.create_index(
        "ix_quote_round_item_next",
        "quote_round_items",
        ["owner_id", "round_id", "consumed_at", "position"],
    )
    op.create_table(
        "daily_quotes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("day_timezone", sa.String(80), nullable=False),
        sa.Column("round_id", sa.String(36), nullable=False),
        sa.Column("quote_id", sa.String(40)),
        sa.Column("quote_text", sa.Text()),
        sa.Column("reason", sa.String(40)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id", "round_id"],
            ["quote_rounds.owner_id", "quote_rounds.id"],
            name="fk_daily_quote_round_owner",
        ),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], name="fk_daily_quote_quote"),
        sa.UniqueConstraint("owner_id", "local_date", name="uq_daily_quote_owner_date"),
        sa.CheckConstraint(
            "(quote_id IS NULL AND quote_text IS NULL) OR (quote_id IS NOT NULL AND quote_text IS NOT NULL)",
            name="ck_daily_quote_snapshot",
        ),
    )
    op.create_index("ix_daily_quote_owner_date", "daily_quotes", ["owner_id", "local_date"])
    op.create_table(
        "quote_operations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("quote_id", sa.String(40), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id", "quote_id"],
            ["quote_preferences.owner_id", "quote_preferences.quote_id"],
            name="fk_quote_operation_preference",
        ),
        sa.UniqueConstraint("owner_id", "key", name="uq_quote_operation_owner_key"),
    )
    op.create_index("ix_quote_operation_owner", "quote_operations", ["owner_id", "created_at"])


def downgrade():
    op.drop_index("ix_quote_operation_owner", table_name="quote_operations")
    op.drop_table("quote_operations")
    op.drop_index("ix_daily_quote_owner_date", table_name="daily_quotes")
    op.drop_table("daily_quotes")
    op.drop_index("ix_quote_round_item_next", table_name="quote_round_items")
    op.drop_table("quote_round_items")
    op.drop_index("ix_quote_round_owner", table_name="quote_rounds")
    op.drop_table("quote_rounds")
    op.drop_index("ix_quote_preference_owner_disliked", table_name="quote_preferences")
    op.drop_index("ix_quote_preference_owner_favorite", table_name="quote_preferences")
    op.drop_table("quote_preferences")
    op.drop_table("quotes")
