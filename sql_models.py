import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from backend.app.database.postgres import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="USER", nullable=False)  # USER, TAROT_READER, SPIRITUAL_CONSULTANT, ADMINISTRATOR
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    palm_readings = relationship("PalmReading", back_populates="user", cascade="all, delete")
    tarot_readings = relationship("TarotReading", back_populates="user", cascade="all, delete")
    recommendations = relationship("Recommendation", back_populates="user", cascade="all, delete")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    age_group = Column(String, nullable=True)
    interests = Column(JSON, default=[], nullable=True)    # List of strings
    goals = Column(JSON, default=[], nullable=True)        # List of strings
    preferences = Column(JSON, default={}, nullable=True)  # Dict config
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="profile")


class TarotCard(Base):
    __tablename__ = "tarot_cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    arcana = Column(String, nullable=False)  # Major, Minor
    suit = Column(String, nullable=True)     # Cups, Wands, Swords, Pentacles, None
    keywords = Column(JSON, default=[], nullable=False)  # List of keywords
    meaning_upright = Column(Text, nullable=False)
    meaning_reversed = Column(Text, nullable=False)
    personality_meaning = Column(Text, nullable=True)
    relationship_meaning = Column(Text, nullable=True)
    career_meaning = Column(Text, nullable=True)
    finance_meaning = Column(Text, nullable=True)
    personal_growth_meaning = Column(Text, nullable=True)
    symbolism = Column(Text, nullable=True)


class PalmReading(Base):
    __tablename__ = "palm_readings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_path = Column(String, nullable=False)
    processed_image_path = Column(String, nullable=True)
    palm_shape = Column(String, nullable=True)
    finger_structure = Column(String, nullable=True)
    
    # Confidence metrics[cite: 1]
    life_line_conf = Column(Float, default=0.0)
    head_line_conf = Column(Float, default=0.0)
    heart_line_conf = Column(Float, default=0.0)
    fate_line_conf = Column(Float, default=0.0)
    sun_line_conf = Column(Float, default=0.0)
    overall_conf = Column(Float, default=0.0)
    
    # Vector keypoints & contour data extracted during CV analysis[cite: 1]
    hand_features = Column(JSON, default={}, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="palm_readings")


class TarotReading(Base):
    __tablename__ = "tarot_readings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    spread_name = Column(String, nullable=False)  # single, three, relationship, career, celtic[cite: 1]
    focus_intent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="tarot_readings")
    cards_drawn = relationship("TarotReadingCard", back_populates="reading", cascade="all, delete")


class TarotReadingCard(Base):
    __tablename__ = "tarot_reading_cards"

    id = Column(Integer, primary_key=True, index=True)
    reading_id = Column(Integer, ForeignKey("tarot_readings.id"), nullable=False)
    card_id = Column(Integer, ForeignKey("tarot_cards.id"), nullable=False)
    position_name = Column(String, nullable=False)
    is_reversed = Column(Boolean, default=False)

    reading = relationship("TarotReading", back_populates="cards_drawn")
    card = relationship("TarotCard")


class AIInterpretation(Base):
    __tablename__ = "ai_interpretations"

    id = Column(Integer, primary_key=True, index=True)
    reading_type = Column(String, nullable=False)  # palm, tarot
    reading_id = Column(Integer, nullable=False)
    summary = Column(Text, nullable=False)
    detailed_insight = Column(Text, nullable=False)
    safety_disclaimer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class GuidanceScore(Base):
    __tablename__ = "guidance_scores"

    id = Column(Integer, primary_key=True, index=True)
    reading_type = Column(String, nullable=False)  # palm, tarot
    reading_id = Column(Integer, nullable=False)
    palm_conf = Column(Float, default=0.0)
    tarot_relevance = Column(Float, default=0.0)
    personality_alignment = Column(Float, default=0.0)
    user_context = Column(Float, default=0.0)
    reading_consistency = Column(Float, default=0.0)
    final_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String, nullable=False)  # career, relationship, growth
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="recommendations")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="notifications")
