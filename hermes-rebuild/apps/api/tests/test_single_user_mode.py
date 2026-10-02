"""单用户模式：打开即是书房，不需要输账号密码。

这是「本机 / 自用部署」的便利开关，不是鉴权绕过：
- 库里仍然只有真实 LoginSession，owner 隔离与 CSRF 全部照旧；
- 生产环境禁止开启（Settings 校验）；
- 关掉开关时行为与从前完全一致（未登录 401）。

最关键的一条是 test_single_user_csrf_survives_across_requests：
自动登录如果每次请求都新建会话，csrf 就会每请求变化，写操作会被 CSRF_INVALID 挡掉。
"""
from uuid import uuid4

from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from hermes_api.cli import migrate
from hermes_api.main import create_app
from hermes_api.settings import Settings
from hermes_api.storage import User

ORIGIN = "http://127.0.0.1:5173"


def make_app(tmp_path, monkeypatch, *, single_user: bool, users=("solo",)):
    url = f"sqlite:///{tmp_path / 'single-user.db'}"
    monkeypatch.setenv("HERMES_DATABASE_URL", url)
    migrate()
    app = create_app(
        Settings(
            database_url=url,
            environment="test",
            single_user_mode=single_user,
            allowed_origin=ORIGIN,
        )
    )
    with Session(app.state.engine) as db:
        for name in users:
            db.add(
                User(
                    id=name,
                    username=name,
                    password_hash=PasswordHasher().hash("QA_TEST_password"),
                    timezone="Asia/Shanghai",
                )
            )
        db.commit()
    return app


def test_single_user_mode_signs_in_without_credentials(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch, single_user=True)
    client = TestClient(app)

    response = client.get("/api/v1/auth/session")

    assert response.status_code == 200, response.text
    assert response.json()["data"]["user"]["username"] == "solo"
    # 会话 cookie 必须真的下发，而不是只在前端伪造登录态
    assert "hermes_session" in response.headers["set-cookie"]


def test_single_user_csrf_survives_across_requests(tmp_path, monkeypatch):
    """自动登录的会话必须跨请求复用，否则写接口全部 CSRF 失败。"""
    app = make_app(tmp_path, monkeypatch, single_user=True)
    client = TestClient(app)

    first = client.get("/api/v1/auth/session").json()["data"]["csrf_token"]
    second = client.get("/api/v1/auth/session").json()["data"]["csrf_token"]
    assert first == second, "单用户会话没有被复用，csrf 每次请求都在变"

    key = str(uuid4())
    created = client.post(
        "/api/v1/learning-sessions",
        json={"operation_id": key, "goal": "QA_TEST_单用户写入"},
        headers={"Origin": ORIGIN, "X-CSRF-Token": first, "Idempotency-Key": key},
    )
    assert created.status_code == 201, created.text


def test_single_user_mode_off_keeps_requiring_sign_in(tmp_path, monkeypatch):
    """开关关掉时行为与从前一致——这条防止便利开关变成默认放行。"""
    app = make_app(tmp_path, monkeypatch, single_user=False)
    client = TestClient(app)

    assert client.get("/api/v1/auth/session").status_code == 401


def test_single_user_mode_with_no_user_still_denies(tmp_path, monkeypatch):
    """库里没有可用用户时不能凭空放行。"""
    app = make_app(tmp_path, monkeypatch, single_user=True, users=())
    client = TestClient(app)

    assert client.get("/api/v1/auth/session").status_code == 401


def test_production_refuses_single_user_mode(monkeypatch):
    """公网部署不允许开成无鉴权。"""
    import pytest

    with pytest.raises(ValueError, match="single-user"):
        Settings(
            environment="production",
            single_user_mode=True,
            database_url="postgresql+psycopg://user@host/db",
            cookie_secure=True,
            allowed_origin="https://hermes.example.com",
            attachment_storage="s3",
            attachment_s3_bucket="private-bucket",
        )
