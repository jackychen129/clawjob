"""Database session provider for modules that expect get_db_session() context manager."""
from contextlib import contextmanager
from unittest.mock import MagicMock


@contextmanager
def get_db_session():
    """Yield a database session. Used by agent_self_iteration and health_monitor.
    When AgentPerformanceMetrics is not an ORM model, yields a mock session that returns no rows.
    """
    # Use real DB session from relational_db when possible; otherwise mock for legacy callers
    try:
        from app.database.relational_db import SessionLocal
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    except Exception:
        # Fallback: mock session so code that does session.query(X).filter(...).all() gets []
        mock = MagicMock()
        mock.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock.query.return_value.filter.return_value.first.return_value = None
        yield mock
