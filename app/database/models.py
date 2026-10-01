from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    Boolean,
    Index,
    func
)
from sqlalchemy.orm import declarative_base
from app.utils.validators import utc_now

Base = declarative_base()


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_url = Column(String(512), nullable=False)
    title = Column(String(256), nullable=False)
    category = Column(String(64), nullable=False)
    content_hash = Column(String(64), nullable=False, unique=True, index=True)
    telegram_message_id = Column(Integer, nullable=True)
    published_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="PENDING", nullable=False, index=True)
    
    # Rich details
    raw_content = Column(Text, nullable=True)
    formatted_post = Column(Text, nullable=True)
    image_url = Column(String(512), nullable=True)
    reliability_score = Column(Integer, default=50)
    confidence_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=utc_now, server_default=func.now())

    __table_args__ = (
        Index("idx_posts_status_published", "status", "published_at"),
    )


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    url = Column(String(512), nullable=False)
    source_type = Column(String(64), nullable=False)  # OFFICIAL_MLBB, OFFICIAL_MPL, ESPORTS, COMMUNITY
    reliability_score = Column(Integer, default=50)
    last_checked_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="ACTIVE")  # ACTIVE, ERROR, DISABLED
    error_count = Column(Integer, default=0)
    last_error_message = Column(Text, nullable=True)


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    league = Column(String(64), nullable=False)  # "MPL ID", "MPL PH"
    season = Column(String(32), nullable=True)
    week = Column(String(32), nullable=True)
    team_a = Column(String(128), nullable=False)
    team_b = Column(String(128), nullable=False)
    date = Column(String(32), nullable=False)  # YYYY-MM-DD
    time = Column(String(32), nullable=True)  # HH:MM
    score_a = Column(Integer, nullable=True)
    score_b = Column(Integer, nullable=True)
    status = Column(String(32), default="upcoming")  # upcoming, live, finished
    mvp = Column(String(128), nullable=True)
    series = Column(String(64), nullable=True)
    source_url = Column(String(512), nullable=True)
    upcoming_notified = Column(Boolean, default=False, server_default="0")
    result_notified = Column(Boolean, default=False, server_default="0")
    created_at = Column(DateTime, default=utc_now, server_default=func.now())

    __table_args__ = (
        Index("idx_matches_league_date", "league", "date"),
    )


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    short_name = Column(String(32), nullable=True)
    league = Column(String(64), nullable=False)
    logo_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=utc_now)


class Hero(Base):
    __tablename__ = "heroes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    role = Column(String(64), nullable=True)
    latest_patch_status = Column(String(32), nullable=True)  # BUFF, NERF, ADJUSTED, UNCHANGED
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class Skin(Base):
    __tablename__ = "skins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hero_name = Column(String(128), nullable=False)
    skin_name = Column(String(128), nullable=False)
    price = Column(String(64), nullable=True)
    release_date = Column(String(64), nullable=True)
    source_url = Column(String(512), nullable=True)
    image_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=utc_now)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    start_date = Column(String(64), nullable=True)
    end_date = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    source_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=utc_now)


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, server_default=func.now())
    level = Column(String(32), nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    component = Column(String(64), nullable=False)  # COLLECTOR, AI, TELEGRAM, SCHEDULER
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(128), nullable=True)
    full_name = Column(String(128), nullable=True)
    added_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utc_now, server_default=func.now())
