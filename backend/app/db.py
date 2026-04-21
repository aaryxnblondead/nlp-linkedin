from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import SQLALCHEMY_DATABASE_URI

engine = create_engine(
	SQLALCHEMY_DATABASE_URI,
	pool_pre_ping=True,
	pool_recycle=1800,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
