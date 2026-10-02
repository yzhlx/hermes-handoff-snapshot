"""Composition root. HTTP owns cookies; use cases own learning decisions."""

import hashlib
import os
import secrets
from dataclasses import asdict

from .advisor_mock import DeterministicAdvisorModel
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .application import LearningService, serialize
from .catalog import get_method, get_situation, list_methods, list_situations
from .domain import PolicyError
from .evidence_routes import create_evidence_router
from .feedback_routes import create_feedback_router
from .knowledge_routes import create_knowledge_router
from .schemas import (
    AuthData,
    CorrectTimeSegmentInput,
    CreateSessionInput,
    EndSessionInput,
    Envelope,
    ErrorEnvelope,
    HealthData,
    LearningMethodData,
    LearningMethodsData,
    LearningSituationData,
    LearningSituationsData,
    LoginInput,
    ProductMeta,
    SessionData,
    SessionHistoryData,
    SubjectsData,
)
from .settings import Settings
from .storage import LoginSession, SQLUnitOfWork, Subject, User, make_engine

COOKIE = "hermes_session"
# 单用户模式复用登录会话的令牌（见 create_app 的 single_user_session 与中间件）。
SINGLE_USER_COOKIE = "hermes_single_user"
PASSWORDS = PasswordHasher()
# A valid hash makes unknown-user login follow the same verification path.
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def advisor_api_key(config) -> str:
    """取 provider 密钥：先环境变量，再 Windows 凭据管理器。

    顺序有意如此——凭据管理器是"本机长期保存"的位置，环境变量是"本次进程"的覆盖。
    两者都拿不到就返回空串，由 build_advisor_model 回落确定性适配器。
    """
    direct = config.provider_api_key.get_secret_value().strip()
    if direct:
        return direct
    if os.name != "nt":
        return ""
    try:
        import subprocess

        result = subprocess.run(
            [
                "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                "$c = Get-StoredCredential -Target 'HermesProvider' -ErrorAction SilentlyContinue;"
                " if ($c) { [Console]::Out.Write($c.GetNetworkCredential().Password) }",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return (result.stdout or "").strip()
    except Exception:  # noqa: BLE001 - 凭据后端不可用不该让应用起不来
        return ""


def build_advisor_model(config):
    """按配置选择 advisor provider。任何缺项都安全回落到确定性适配器。"""
    key = advisor_api_key(config)
    if not (config.provider_base_url and key and config.provider_model):
        return DeterministicAdvisorModel()
    try:
        from .openai_model import OpenAIModel

        return OpenAIModel(
            config.provider_base_url,
            key,
            config.provider_model,
            timeout=config.provider_timeout_seconds,
            max_tokens=config.provider_max_tokens,
            supports_image=config.provider_supports_image,
        )
    except Exception:  # noqa: BLE001 - 配置有问题时宁可降级也不让服务起不来
        return DeterministicAdvisorModel()


def create_app(settings: Settings | None = None):
    config = settings or Settings()
    app = FastAPI(title="Hermes API", version="0.1.0")
    engine = make_engine(config.database_url)
    app.state.engine = engine
    app.state.settings = config
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[config.allowed_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=[
            "Content-Type",
            "X-CSRF-Token",
            "Idempotency-Key",
            "If-Match",
            "If-None-Match",
        ],
    )

    @app.middleware("http")
    async def request_id(request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        return response

    def envelope(request, value):
        return {"data": value, "meta": {"request_id": request.state.request_id}}

    @app.exception_handler(PolicyError)
    async def policy_error(request, error):
        payload = {
            "code": error.code,
            "message": error.message,
            "request_id": request.state.request_id,
        }
        if hasattr(error, "current_version"):
            payload["current_version"] = error.current_version
        if hasattr(error, "current"):
            payload["current"] = error.current
        return JSONResponse({"error": payload}, status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return await policy_error(request, PolicyError("VALIDATION_ERROR", "Invalid request.", 422))

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, error):
        return await policy_error(
            request, PolicyError("SERVICE_UNAVAILABLE", "Storage unavailable.", 503)
        )

    def database():
        with Session(engine) as db:
            yield db

    @app.middleware("http")
    async def persist_single_user_token(request: Request, call_next):
        """把单用户自动登录新签发的令牌写进 cookie，让后续请求复用同一个会话。

        不这么做的话每次请求都会新建会话（csrf 也随之变化），写接口必然 CSRF 失败。
        令牌本身是随机会话标识，不是密码，也不代表任何绕过——它对应库里一条真实的 LoginSession。
        """
        response = await call_next(request)
        token = getattr(request.state, "single_user_token", None)
        if token:
            response.set_cookie(
                SINGLE_USER_COOKIE,
                token,
                httponly=True,
                secure=config.cookie_secure,
                samesite="lax",
                max_age=config.session_hours * 3600,
                path="/api/v1",
            )
        return response

    def identity(request: Request, db: Session = Depends(database)):
        token = request.cookies.get(COOKIE, "")
        login = db.get(LoginSession, digest(token)) if token else None
        now = datetime.now(UTC)
        expiry = login.expires_at.replace(tzinfo=UTC) if login else now
        user = db.get(User, login.owner_id) if login else None
        if not login or not user or expiry <= now:
            if not config.single_user_mode:
                raise PolicyError("UNAUTHENTICATED", "Sign in to continue.", 401)
            # 单用户模式：本机 / 自用部署打开即是书房。
            #
            # 令牌必须**持久化在 cookie 里复用**，不能每次请求新建会话：
            # 登录会话带着 csrf，而写接口要求 X-CSRF-Token 等于会话的 csrf。
            # 若每次请求都换新会话，前端拿到的 csrf 与后端校验的那一个不是同一个，
            # 所有写操作都会被 CSRF_INVALID 挡掉。
            login, user = single_user_session(request, db)
            if login is None:
                raise PolicyError("UNAUTHENTICATED", "Sign in to continue.", 401)
        if getattr(user, "status", "active") == "deleted":
            raise PolicyError("UNAUTHENTICATED", "Sign in to continue.", 401)
        return user, login

    def single_user_session(request: Request, db: Session):
        """单用户模式：为唯一用户取回或建立持久的登录会话（含 cookie 回写）。

        返回 (login, user)；库里没有可用用户时返回 (None, None)，由调用方转成 401。
        """
        user = db.scalar(
            select(User).where(User.status == "active").order_by(User.id).limit(1)
        )
        if user is None:
            return None, None
        existing_token = request.cookies.get(SINGLE_USER_COOKIE, "")
        login = db.get(LoginSession, digest(existing_token)) if existing_token else None
        if login is not None:
            expires = login.expires_at.replace(tzinfo=UTC)
            if login.owner_id != user.id or expires <= datetime.now(UTC):
                db.delete(login)
                login = None
        if login is None:
            token = secrets.token_urlsafe(48)
            login = LoginSession(
                token_hash=digest(token),
                owner_id=user.id,
                csrf=secrets.token_urlsafe(32),
                expires_at=datetime.now(UTC) + timedelta(hours=config.session_hours),
            )
            db.add(login)
            db.commit()
            request.state.single_user_token = token
        return login, user

    def sanitized_write(request: Request, auth=Depends(identity)):
        """Origin + CSRF only.

        Cancelling a pending deletion must stay reachable even while the account
        is otherwise write-blocked, so this dependency omits that guard.
        """
        if request.headers.get("origin") != config.allowed_origin:
            raise PolicyError("FORBIDDEN", "Request origin is not allowed.", 403)
        if not secrets.compare_digest(request.headers.get("x-csrf-token", ""), auth[1].csrf):
            raise PolicyError("CSRF_INVALID", "Refresh your session before retrying.", 403)
        return auth

    def authorized_write(request: Request, auth=Depends(sanitized_write)):
        if getattr(auth[0], "status", "active") == "deletion_pending":
            raise PolicyError(
                "ACCOUNT_PENDING_DELETION",
                "This account is pending deletion. Cancel the request to keep using it.",
                403,
            )
        return auth

    def auth_data(user, login):
        return {
            "user": {"id": user.id, "username": user.username, "timezone": user.timezone},
            "csrf_token": login.csrf,
        }

    errors = {code: {"model": ErrorEnvelope} for code in (401, 403, 404, 409, 422, 428, 503)}

    @app.get("/api/v1/health/live", response_model=Envelope[HealthData])
    def live(request: Request):
        return envelope(request, {"status": "ok"})

    @app.get("/api/v1/health/ready", response_model=Envelope[HealthData], responses=errors)
    def ready(request: Request, db: Session = Depends(database)):
        db.execute(text("SELECT 1"))
        db.execute(select(User.id).limit(1))
        return envelope(request, {"status": "ok"})

    @app.get("/api/v1/meta", response_model=Envelope[ProductMeta])
    def metadata(request: Request):
        return envelope(request, ProductMeta(environment=config.environment))

    @app.post("/api/v1/auth/login", response_model=Envelope[AuthData], responses=errors)
    def login(
        body: LoginInput, request: Request, response: Response, db: Session = Depends(database)
    ):
        if request.headers.get("origin") != config.allowed_origin:
            raise PolicyError("FORBIDDEN", "Request origin is not allowed.", 403)
        user = db.scalar(select(User).where(User.username == body.username))
        try:
            PASSWORDS.verify(user.password_hash if user else DUMMY_HASH, body.password)
        except VerificationError:
            raise PolicyError(
                "INVALID_CREDENTIALS", "Username or password is incorrect.", 401
            ) from None
        if user is None:
            raise PolicyError("INVALID_CREDENTIALS", "Username or password is incorrect.", 401)
        old = request.cookies.get(COOKIE)
        if old and (previous := db.get(LoginSession, digest(old))):
            db.delete(previous)
        token = secrets.token_urlsafe(48)
        login = LoginSession(
            token_hash=digest(token),
            owner_id=user.id,
            csrf=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + timedelta(hours=config.session_hours),
        )
        db.add(login)
        db.commit()
        response.set_cookie(
            COOKIE,
            token,
            httponly=True,
            secure=config.cookie_secure,
            samesite="lax",
            max_age=config.session_hours * 3600,
            path="/api/v1",
        )
        return envelope(request, auth_data(user, login))

    @app.get("/api/v1/auth/session", response_model=Envelope[AuthData], responses=errors)
    def session(request: Request, response: Response, auth=Depends(identity)):
        # 单用户模式首次自动登录时，会话令牌已经签发，这里把正式会话 cookie 一并写回，
        # 让前端拿到的会话与后续请求用的是同一条 LoginSession（含同一个 csrf）。
        token = getattr(request.state, "single_user_token", None)
        if token:
            response.set_cookie(
                COOKIE,
                token,
                httponly=True,
                secure=config.cookie_secure,
                samesite="lax",
                max_age=config.session_hours * 3600,
                path="/api/v1",
            )
        return envelope(request, auth_data(*auth))

    @app.post("/api/v1/auth/logout", status_code=204, responses=errors)
    def logout(response: Response, auth=Depends(authorized_write), db: Session = Depends(database)):
        db.delete(auth[1])
        db.commit()
        response.delete_cookie(
            COOKIE, path="/api/v1", secure=config.cookie_secure, httponly=True, samesite="lax"
        )

    @app.get("/api/v1/subjects", response_model=Envelope[SubjectsData], responses=errors)
    def subjects(request: Request, auth=Depends(identity), db: Session = Depends(database)):
        from .catalog import subject_group_label

        rows = db.scalars(
            select(Subject).where(Subject.owner_id == auth[0].id).order_by(Subject.name)
        )
        return envelope(
            request,
            {
                "items": [
                    {"id": row.id, "name": row.name, "group_label": subject_group_label(row.name)}
                    for row in rows
                ]
            },
        )

    @app.get(
        "/api/v1/learning-methods",
        response_model=Envelope[LearningMethodsData],
        responses=errors,
    )
    def learning_methods(request: Request):
        return envelope(
            request, {"items": [LearningMethodData(**asdict(item)) for item in list_methods()]}
        )

    @app.get(
        "/api/v1/learning-methods/{method_id}",
        response_model=Envelope[LearningMethodData],
        responses=errors,
    )
    def learning_method(method_id: str, request: Request):
        value = get_method(method_id)
        if value is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return envelope(request, LearningMethodData(**asdict(value)))

    @app.get(
        "/api/v1/learning-situations",
        response_model=Envelope[LearningSituationsData],
        responses=errors,
    )
    def learning_situations(request: Request):
        return envelope(
            request,
            {"items": [LearningSituationData(**asdict(item)) for item in list_situations()]},
        )

    @app.get(
        "/api/v1/learning-situations/{situation_id}",
        response_model=Envelope[LearningSituationData],
        responses=errors,
    )
    def learning_situation(situation_id: str, request: Request):
        value = get_situation(situation_id)
        if value is None:
            raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
        return envelope(request, LearningSituationData(**asdict(value)))

    @app.get(
        "/api/v1/learning-sessions/current",
        response_model=Envelope[SessionData | None],
        responses=errors,
    )
    def current(request: Request, auth=Depends(identity), db: Session = Depends(database)):
        value = SQLUnitOfWork(db).sessions.current(auth[0].id)
        return envelope(request, serialize(value) if value else None)

    @app.get(
        "/api/v1/learning-sessions",
        response_model=Envelope[SessionHistoryData],
        responses=errors,
    )
    def session_history(
        request: Request,
        limit: int = 20,
        cursor: UUID | None = None,
        auth=Depends(identity),
        db: Session = Depends(database),
    ):
        if not 1 <= limit <= 100:
            raise PolicyError("VALIDATION_ERROR", "Limit must be between 1 and 100.", 422)
        rows = SQLUnitOfWork(db).sessions.list(
            auth[0].id, limit + 1, str(cursor) if cursor else None
        )
        has_more = len(rows) > limit
        values = rows[:limit]
        return envelope(
            request,
            {
                "items": [serialize(value) for value in values],
                "next_cursor": values[-1].id if has_more and values else None,
            },
        )

    @app.get(
        "/api/v1/learning-sessions/{session_id}",
        response_model=Envelope[SessionData],
        responses=errors,
    )
    def session_detail(
        session_id: UUID, request: Request, auth=Depends(identity), db: Session = Depends(database)
    ):
        value = SQLUnitOfWork(db).sessions.get(auth[0].id, str(session_id))
        return envelope(request, serialize(value))

    @app.post(
        "/api/v1/learning-sessions",
        status_code=201,
        response_model=Envelope[SessionData],
        responses=errors,
    )
    def start(
        body: CreateSessionInput,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
    ):
        value = LearningService(SQLUnitOfWork(db)).execute(
            auth[0].id, auth[0].timezone, "create", body.model_dump(mode="json"), idempotency_key
        )
        return envelope(request, value)

    @app.post(
        "/api/v1/learning-sessions/{session_id}/end",
        response_model=Envelope[SessionData],
        responses=errors,
    )
    def end(
        session_id: UUID,
        body: EndSessionInput,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        try:
            version = int(if_match.strip('"')) if if_match else None
        except ValueError:
            raise PolicyError(
                "VALIDATION_ERROR", "If-Match must be a version number.", 422
            ) from None
        value = LearningService(SQLUnitOfWork(db)).execute(
            auth[0].id,
            auth[0].timezone,
            "end",
            body.model_dump(mode="json"),
            idempotency_key,
            str(session_id),
            version,
        )
        return envelope(request, value)

    def transition(
        action: str,
        session_id: UUID,
        body: EndSessionInput,
        request: Request,
        auth,
        db: Session,
        idempotency_key: str,
        if_match: str | None,
    ):
        try:
            version = int(if_match.strip('"')) if if_match else None
        except ValueError:
            raise PolicyError(
                "VALIDATION_ERROR", "If-Match must be a version number.", 422
            ) from None
        value = LearningService(SQLUnitOfWork(db)).execute(
            auth[0].id,
            auth[0].timezone,
            action,
            body.model_dump(mode="json"),
            idempotency_key,
            str(session_id),
            version,
        )
        return envelope(request, value)

    def action_route(action: str):
        def route(
            session_id: UUID,
            body: EndSessionInput,
            request: Request,
            auth=Depends(authorized_write),
            db: Session = Depends(database),
            idempotency_key: str = Header(default=""),
            if_match: str | None = Header(default=None),
        ):
            return transition(
                action, session_id, body, request, auth, db, idempotency_key, if_match
            )

        return route

    for action in ("pause", "resume", "cancel"):
        app.add_api_route(
            f"/api/v1/learning-sessions/{{session_id}}/{action}",
            action_route(action),
            methods=["POST"],
            response_model=Envelope[SessionData],
            responses=errors,
            name=f"{action}_learning_session",
        )

    @app.patch(
        "/api/v1/learning-sessions/{session_id}/time-segments/{segment_id}",
        response_model=Envelope[SessionData],
        responses=errors,
    )
    def correct_time_segment(
        session_id: UUID,
        segment_id: UUID,
        body: CorrectTimeSegmentInput,
        request: Request,
        auth=Depends(authorized_write),
        db: Session = Depends(database),
        idempotency_key: str = Header(default=""),
        if_match: str | None = Header(default=None),
    ):
        try:
            version = int(if_match.strip().strip('"')) if if_match else None
        except ValueError:
            raise PolicyError(
                "VALIDATION_ERROR", "If-Match must be a version number.", 422
            ) from None
        if version is not None and version < 1:
            raise PolicyError("VALIDATION_ERROR", "If-Match must be positive.", 422)
        value = LearningService(SQLUnitOfWork(db)).correct_segment(
            auth[0].id,
            str(session_id),
            str(segment_id),
            body.model_dump(mode="json"),
            idempotency_key,
            version,
        )
        return envelope(request, value)

    app.include_router(create_feedback_router(database, identity, authorized_write))
    app.include_router(create_knowledge_router(database, identity, authorized_write))
    app.include_router(create_evidence_router(database, identity, authorized_write))
    from .attachment_routes import create_attachment_router

    app.include_router(create_attachment_router(database, identity, authorized_write, config))
    from . import quotes_storage  # noqa: F401
    from .quotes import create_quotes_router

    app.include_router(create_quotes_router(database, identity, authorized_write))
    from .records_routes import create_records_router
    from .suggestion_routes import create_suggestion_router

    app.include_router(create_suggestion_router(database, identity, authorized_write))
    app.include_router(create_records_router(database, identity))
    from .home_routes import create_home_router

    app.include_router(create_home_router(engine, identity))
    from .comparison_routes import create_comparison_router

    app.include_router(create_comparison_router(database, identity, authorized_write))
    from .stuck_point_routes import create_stuck_point_router

    app.include_router(create_stuck_point_router(database, identity, authorized_write))
    from .advisor_mock import DeterministicAdvisorModel
    from .advisor_routes import create_advisor_router

    # 有凭据就用真实 OpenAI 兼容 provider；没有就回落确定性适配器（测试与离线运行照旧）。
    # 用例层不感知协议：两条路径都只暴露 analyze()/model_id/capabilities。
    app.state.advisor_model = build_advisor_model(config)
    app.include_router(create_advisor_router(database, identity, authorized_write))
    from .account_routes import create_account_router

    app.include_router(create_account_router(database, identity, sanitized_write))
    return app


app = create_app()
