"""Pure rules for account data sovereignty (03 §9).

An export gives the owner their own records; a deletion is an explicit,
reversible-until-it-is-not state change. Nothing here reaches the network or the
database, and nothing here invents data the learner did not create.
"""

from datetime import UTC, datetime, timedelta

from .domain import PolicyError

# Typed verbatim by the user; a checkbox is too easy to click by accident.
CONFIRMATION_PHRASE = "DELETE MY ACCOUNT"
# The revoke window and the export lifetime are deployment policy (03 §9 keeps
# them open until deployment review), so they are named constants, not magic.
REVOKE_WINDOW_HOURS = 24
EXPORT_TTL_HOURS = 24
MAX_EXPORT_BYTES = 20 * 1024 * 1024

# Never exported: credentials, authentication sessions and idempotency caches.
NEVER_EXPORTED_TABLES = ("users", "login_sessions", "operations", "quote_operations")
# Columns that are secrets or storage internals rather than study content.
SECRET_COLUMNS = ("password_hash", "token_hash", "csrf", "object_key", "payload")


def check_confirmation(value):
    text = (value or "").strip()
    if text != CONFIRMATION_PHRASE:
        raise PolicyError(
            "VALIDATION_ERROR",
            f'Type "{CONFIRMATION_PHRASE}" exactly to confirm.',
            422,
        )
    return text


def purge_after(now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)) + timedelta(hours=REVOKE_WINDOW_HOURS)


def export_expiry(now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)) + timedelta(hours=EXPORT_TTL_HOURS)


def build_impact(counts: dict[str, int]) -> dict:
    """What deletion removes, stated in plain terms before anything happens."""
    total = sum(counts.values())
    return {
        "total_records": total,
        "by_table": counts,
        "deleted": [
            "你的学习记录、题目、作答、卡壳点、对比、自评与建议",
            "私有附件原件与已生成的预览",
            "导出包与临时文件",
            "登录会话与认证凭据",
        ],
        "note": "删除后服务端不再保留你的学习内容，无法从这里恢复。",
    }


def impact_summary(impact: dict) -> str:
    return f"将清除你名下 {impact['total_records']} 条记录，以及私有附件与导出包。"
