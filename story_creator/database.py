# story_creator/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

DATABASE_URI = 'sqlite:///story_creator.db'

engine = create_engine(
    DATABASE_URI,
    connect_args={"check_same_thread": False}
)

# Use scoped_session for thread safety
SessionFactory = sessionmaker(bind=engine)
SessionLocal = scoped_session(SessionFactory)
