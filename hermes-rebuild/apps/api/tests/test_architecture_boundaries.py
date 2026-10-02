"""Keep application policy independent from HTTP and database adapters."""

import ast
from pathlib import Path

import pytest


def forbidden_imports(source: str) -> list[str]:
    names = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    return [
        name
        for name in names
        if name.split(".")[0]
        in {"fastapi", "sqlalchemy", "alembic", "boto3", "botocore", "PIL", "pypdf", "pypdfium2"}
        or name.split(".")[-1] == "storage"
        or name.split(".")[-1].endswith(
            ("_storage", "_routes", "_object_store", "_validation", "_worker")
        )
    ]


@pytest.mark.parametrize(
    "module",
    [
        "domain",
        "application",
        "ports",
        "feedback",
        "knowledge_domain",
        "knowledge_service",
        "knowledge_ports",
        "evidence_domain",
        "evidence_service",
        "evidence_ports",
        "attachment_domain",
        "attachment_service",
        "attachment_ports",
        "suggestion_domain",
        "suggestion_service",
        "suggestion_ports",
        "records_domain",
        "records_service",
        "records_ports",
        "home_ports",
        "home_service",
        "comparison_domain",
        "comparison_ports",
        "comparison_service",
        "stuck_point_domain",
        "stuck_point_ports",
        "stuck_point_service",
        "advisor_domain",
        "advisor_ports",
        "advisor_service",
        "account_domain",
        "account_ports",
        "account_service",
    ],
)
def test_policy_modules_do_not_import_infrastructure(module):
    root = Path(__file__).parents[1] / "src" / "hermes_api"
    assert forbidden_imports((root / f"{module}.py").read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    "source",
    [
        "import sqlalchemy as sql",
        "from fastapi import Request",
        "from .storage import Base",
        "from .knowledge_storage import KnowledgePointRow",
        "from hermes_api.evidence_routes import create_evidence_router",
        "from PIL import Image",
        "import boto3",
        "from .attachment_object_store import make_store",
    ],
)
def test_boundary_guard_detects_absolute_and_relative_imports(source):
    assert forbidden_imports(source)
