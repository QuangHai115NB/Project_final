from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Quan hệ với CV và JD của người dùng
    cvs = relationship("CVDocument", back_populates="user", cascade="all, delete-orphan")
    jds = relationship("JDDocument", back_populates="user", cascade="all, delete-orphan")
    matches = relationship("MatchHistory", back_populates="user", cascade="all, delete-orphan")


class CVDocument(Base):
    __tablename__ = "cv_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    content_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Quan hệ với bảng `User` và `MatchHistory`
    user = relationship("User", back_populates="cvs")
    matches = relationship("MatchHistory", back_populates="cv")


class JDDocument(Base):
    __tablename__ = "jd_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    content_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Quan hệ với bảng `User` và `MatchHistory`
    user = relationship("User", back_populates="jds")
    matches = relationship("MatchHistory", back_populates="jd")


class MatchHistory(Base):
    __tablename__ = "match_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cv_id = Column(Integer, ForeignKey("cv_documents.id"), nullable=False)
    jd_id = Column(Integer, ForeignKey("jd_documents.id"), nullable=False)
    similarity_score = Column(Float, nullable=True)
    report_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Quan hệ với bảng `User`, `CVDocument`, `JDDocument`
    user = relationship("User", back_populates="matches")
    cv = relationship("CVDocument", back_populates="matches")
    jd = relationship("JDDocument", back_populates="matches")