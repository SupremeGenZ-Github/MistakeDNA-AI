from alembic import context
from app.db import make_engine
from app.config import settings
from app.models import Base

def run_migrations_online():
    engine=make_engine(settings.database_url)
    with engine.connect() as connection:
        context.configure(connection=connection,target_metadata=Base.metadata,compare_type=True)
        with context.begin_transaction(): context.run_migrations()

if context.is_offline_mode():
    from app.db import normalize_url
    context.configure(url=normalize_url(settings.database_url),target_metadata=Base.metadata,literal_binds=True,dialect_opts={'paramstyle':'named'})
    with context.begin_transaction(): context.run_migrations()
else:
    run_migrations_online()
