from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

from app.config import settings

os.makedirs(os.path.dirname(settings.sqlite_path), exist_ok=True)

engine = create_engine(f"sqlite:///{settings.sqlite_path}", echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True)
    user_message = Column(Text)
    agent_response = Column(Text)
    intent = Column(String(100))
    tools_used = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    memory_type = Column(String(50))
    content = Column(Text)
    meta_data = Column(JSON, default=dict)
    importance = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(String(100))
    test_case_name = Column(String(200))
    intent = Column(String(100))
    input_text = Column(Text)
    expected_output = Column(Text)
    actual_output = Column(Text)
    success = Column(Boolean)
    metrics = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True)
    step = Column(String(50))
    action = Column(String(100))
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    error = Column(Text)
    duration_ms = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class BusinessData(Base):
    __tablename__ = "business_data"

    id = Column(Integer, primary_key=True, index=True)
    data_type = Column(String(50))
    external_id = Column(String(100))
    title = Column(String(500))
    content = Column(Text)
    meta_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
