"""Database initialization and table creation helper."""
from backend.app.db.session import engine, Base
import backend.app.models # noqa: F401


def init_db():
    """Create all tables in the configured database."""
    Base.metadata.create_all(bind=engine)


def reset_db():
    """Drop and recreate all tables (useful for test fixtures or local reset)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    print("Initializing database tables...")
    init_db()
    print("Database tables initialized successfully.")
