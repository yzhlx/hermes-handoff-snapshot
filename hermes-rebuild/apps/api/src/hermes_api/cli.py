"""Explicit operational commands; never migrate on HTTP server startup."""

import argparse
import getpass
import json
import os
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from alembic import command
from alembic.config import Config
from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from .settings import Settings
from .storage import Subject, User, make_engine


def migrate():
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    command.upgrade(config, "head")


def bootstrap(username, password, timezone_name="Asia/Shanghai"):
    if len(password) < 12:
        raise ValueError("Use a password with at least 12 characters.")
    ZoneInfo(timezone_name)
    with Session(make_engine(Settings().database_url)) as db:
        if db.scalar(select(User.id).where(User.username == username)):
            raise ValueError("Username already exists; bootstrap does not overwrite accounts.")
        owner = str(uuid4())
        db.add(
            User(
                id=owner,
                username=username,
                password_hash=PasswordHasher().hash(password),
                timezone=timezone_name,
            )
        )
        db.flush()
        for name in ("信号与系统", "电路基础", "高等数学", "英语", "政治"):
            db.add(Subject(id=str(uuid4()), owner_id=owner, name=name))
        db.commit()


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate")
    user = sub.add_parser("bootstrap")
    user.add_argument("--username", required=True)
    user.add_argument("--timezone", default="Asia/Shanghai")
    export = sub.add_parser("export-openapi")
    export.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "migrate":
        migrate()
    elif args.command == "bootstrap":
        password = os.environ.get("HERMES_BOOTSTRAP_PASSWORD") or getpass.getpass("Password: ")
        bootstrap(args.username, password, args.timezone)
    else:
        from .main import create_app

        Path(args.output).write_text(
            json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
