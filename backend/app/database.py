import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATABASE_URL = f"sqlite:///{os.path.join(BACKEND_DIR, 'etsy_laser_auto.db')}"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Enable WAL (Write-Ahead Logging) mode and synchronous=NORMAL
# to prevent database locking during concurrent operations.
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
