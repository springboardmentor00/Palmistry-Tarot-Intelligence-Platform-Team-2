from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=120)
    age_group: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    goals: List[str] = Field(default_factory=list)


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


class UserProfileUpdate(BaseModel):
    age_group: Optional[str] = None
    interests: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    age_group: Optional[str]
    interests: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    profile: Optional[UserProfileResponse] = None


class PalmReadingCreate(BaseModel):
    image_base64: str = Field(..., min_length=100)


class PalmReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    image_path: str
    processed_image_path: Optional[str]
    palm_shape: Optional[str]
    finger_structure: Optional[str]
    life_line_conf: float
    head_line_conf: float
    heart_line_conf: float
    fate_line_conf: float
    sun_line_conf: float
    overall_conf: float
    created_at: datetime
    summary: Optional[str] = None
    detailed_insight: Optional[str] = None
    safety_disclaimer: Optional[str] = None
    guidance_score: Optional[float] = None


class TarotCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    arcana: str
    suit: Optional[str]
    keywords: List[str]
    meaning_upright: str
    meaning_reversed: str
    symbolism: Optional[str]


class TarotReadingCreate(BaseModel):
    spread_name: str = Field(..., min_length=1, max_length=80)
    focus_intent: Optional[str] = Field(default="General", max_length=500)
    card_ids: Optional[List[int]] = None
    reversed_flags: Optional[List[bool]] = None


class TarotReadingCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    position_name: str
    is_reversed: bool
    card: TarotCardResponse


class TarotReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    spread_name: str
    focus_intent: Optional[str]
    created_at: datetime
    cards_drawn: List[TarotReadingCardResponse]
    summary: Optional[str] = None
    detailed_insight: Optional[str] = None
    safety_disclaimer: Optional[str] = None
    guidance_score: Optional[float] = None


class AIInterpretationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    reading_type: str
    reading_id: int
    summary: str
    detailed_insight: str
    safety_disclaimer: str
    created_at: datetime


class GuidanceScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    reading_type: str
    reading_id: int
    palm_conf: float
    tarot_relevance: float
    personality_alignment: float
    user_context: float
    reading_consistency: float
    final_score: float
    created_at: datetime


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category: str
    title: str
    description: str
    is_completed: bool
    created_at: datetime


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime


class AdminAnalyticsResponse(BaseModel):
    total_users: int
    active_users: int
    total_readings: int
    palm_readings: int
    tarot_readings: int
    avg_guidance_score: Optional[float] = None
    api_response_time_ms: Optional[float] = None


class UserManageUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class ComprehensiveInsightResponse(BaseModel):
    summary: str
    categories: Dict[str, str]
    sources_used: List[str]
    safety_disclaimer: str
    generated_at: datetime


class CombinedReadingCreate(BaseModel):
    image_base64: Optional[str] = None
    palm_reading_id: Optional[int] = None
    spread_name: str = Field(default="three", max_length=80)
    focus_intent: Optional[str] = Field(default="Life Path & Purpose Alignment", max_length=500)
    user_name: Optional[str] = Field(default=None, max_length=120)
    card_ids: Optional[List[int]] = None
    reversed_flags: Optional[List[bool]] = None


class CombinedMasterReportResponse(BaseModel):
    id: int
    user_name: str
    summary: str
    composite_score: float
    categories: Dict[str, str]
    palm_metrics: Dict[str, Any]
    tarot_cards: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    safety_disclaimer: str
    created_at: datetime


class UserAnalyticsResponse(BaseModel):
    reading_count: int
    palm_readings: int
    tarot_readings: int
    average_guidance_score: Optional[float]
    recommendation_count: int
    completed_recommendations: int
    completion_rate: float
    readings_by_day: List[Dict[str, Any]]
    score_by_day: List[Dict[str, Any]]
    recent_readings: List[Dict[str, Any]]


class ExecutiveAnalyticsResponse(BaseModel):
    total_users: int
    active_users: int
    new_users_30d: int
    total_readings: int
    palm_readings: int
    tarot_readings: int
    average_guidance_score: Optional[float]
    recommendation_completion_rate: float
    role_breakdown: Dict[str, int]
    readings_by_day: List[Dict[str, Any]]
    scores_by_day: List[Dict[str, Any]]
    api_requests: int
    average_api_latency_ms: Optional[float]
    error_requests: int


class SpecialistAnalyticsResponse(BaseModel):
    client_count: int
    reading_count: int
    average_guidance_score: Optional[float]
    readings_by_day: List[Dict[str, Any]]
    recent_readings: List[Dict[str, Any]]
    category_breakdown: Dict[str, int] = Field(default_factory=dict)
    repeat_client_count: int = 0
    readings_30d: int = 0
    active_days_30d: int = 0
    average_readings_per_client: Optional[float] = None
    repeat_client_rate: float = 0.0
    latest_session_at: Optional[str] = None
    report_ready_count: int = 0
