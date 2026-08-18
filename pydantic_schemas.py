from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

# Auth Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    role: Optional[str] = "USER"  # <--- ADDED: Allows registering with custom roles
    age_group: Optional[str] = "25-34"
    interests: List[str] = []
    goals: List[str] = []

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

# Profile Schemas
class UserProfileUpdate(BaseModel):
    age_group: Optional[str] = None
    interests: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None

class UserProfileResponse(BaseModel):
    age_group: Optional[str]
    interests: List[str]
    goals: List[str]
    preferences: Dict[str, Any]

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    profile: Optional[UserProfileResponse] = None

    class Config:
        from_attributes = True

# Palm Analysis Schemas
class PalmReadingCreate(BaseModel):
    image_base64: str  # Upload image as base64 string for quick API processing

class PalmReadingResponse(BaseModel):
    id: int
    image_path: str
    processed_image_path: Optional[str]
    palm_shape: Optional[str]
    finger_structure: Optional[str]
    life_line_conf: float
    head_line_conf: float
    heart_line_conf: float
    fate_line_conf: float
    overall_conf: float
    created_at: datetime

    class Config:
        from_attributes = True

# Tarot Schemas
class TarotCardResponse(BaseModel):
    id: int
    name: str
    arcana: str
    suit: Optional[str]
    keywords: List[str]
    meaning_upright: str
    meaning_reversed: str
    symbolism: Optional[str]

    class Config:
        from_attributes = True

class TarotReadingCreate(BaseModel):
    spread_name: str  # single, three, celtic
    focus_intent: Optional[str] = "General"

class TarotReadingCardResponse(BaseModel):
    position_name: str
    is_reversed: bool
    card: TarotCardResponse

    class Config:
        from_attributes = True

class TarotReadingResponse(BaseModel):
    id: int
    spread_name: str
    focus_intent: Optional[str]
    created_at: datetime
    cards_drawn: List[TarotReadingCardResponse]

    class Config:
        from_attributes = True

# AI Interpretation
class AIInterpretationResponse(BaseModel):
    reading_type: str
    reading_id: int
    summary: str
    detailed_insight: str
    safety_disclaimer: str
    created_at: datetime

    class Config:
        from_attributes = True

# Guidance Score
class GuidanceScoreResponse(BaseModel):
    reading_type: str
    reading_id: int
    palm_conf: float
    tarot_relevance: float
    personality_alignment: float
    user_context: float
    reading_consistency: float
    final_score: float
    created_at: datetime

    class Config:
        from_attributes = True

# Recommendations
class RecommendationResponse(BaseModel):
    id: int
    category: str
    title: str
    description: str
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Notifications
class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Admin / Telemetry Analytics
class AdminAnalyticsResponse(BaseModel):
    total_users: int
    active_users: int
    total_readings: int
    palm_readings: int
    tarot_readings: int
    avg_guidance_score: float
    api_response_time_ms: int

class UserManageUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
