from alembic import context

from hermes_api import (
    attachment_storage,  # noqa: F401 - register attachment tables
    comparison_storage,  # noqa: F401 - register comparison tables
    evidence_storage,  # noqa: F401 - register evidence tables
    knowledge_storage,  # noqa: F401 - register knowledge tables
    quotes_storage,  # noqa: F401 - register quote tables in migration metadata
    suggestion_storage,  # noqa: F401 - register suggestion tables
)
from hermes_api.settings import Settings
from hermes_api.storage import Base, make_engine

if context.is_offline_mode():
    context.configure(
        url=Settings().database_url, target_metadata=Base.metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with make_engine(Settings().database_url).connect() as connection:
        sqlite_fk_disabled = connection.dialect.name == "sqlite"
        if sqlite_fk_disabled:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
        try:
            context.configure(connection=connection, target_metadata=Base.metadata)
            with context.begin_transaction():
                context.run_migrations()
            if sqlite_fk_disabled:
                connection.commit()
        except Exception:
            if sqlite_fk_disabled:
                connection.rollback()
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                connection.commit()
            raise
        if sqlite_fk_disabled:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
            violations = connection.exec_driver_sql("PRAGMA foreign_key_check").all()
            if violations:
                raise RuntimeError(f"Migration left foreign key violations: {violations!r}")
