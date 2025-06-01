"""Data models for the Speaking Meeting Bot API."""

from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class PersonaBase(BaseModel):
    name: str
    description: Optional[str] = None
    personality: Optional[str] = None
    knowledge_base: Optional[str] = None
    image: Optional[str] = None


class PersonaCreate(PersonaBase):
    pass


class PersonaUpdate(PersonaBase):
    pass


class Persona(PersonaBase):
    id: str

    class Config:
        from_attributes = True


class BotRequest(BaseModel):
    """Request model for creating a speaking bot in a meeting."""

    # Define ONLY the fields we want in our API
    meeting_url: str = Field(
        ...,
        description="URL of the Google Meet, Zoom or Microsoft Teams meeting to join",
    )
    bot_name: str = Field("", description="Name to display for the bot in the meeting")
    personas: Optional[List[str]] = Field(
        None,
        description="List of persona names to use. The first available will be selected.",
    )
    bot_image: Optional[str] = None
    entry_message: Optional[str] = None
    text_message: Optional[str] = None
    context_info: Optional[str] = Field(
        None,
        description="Additional context information to inform the bot's responses and behavior",
    )
    extra: Optional[Dict[str, Any]] = None
    enable_tools: bool = True
    webhook_url: Optional[str] = None

    # NOTE: streaming_audio_frequency is intentionally excluded and handled internally

    class Config:
        json_schema_extra = {
            "example": {
                "meeting_url": "https://meet.google.com/abc-defg-hij",
                "bot_name": "Meeting Assistant",
                "personas": ["helpful_assistant", "meeting_facilitator"],
                "bot_image": "https://example.com/bot-avatar.png",
                "entry_message": "Hello! I'm here to assist with the meeting.",
                "text_message": "Meeting Assistant has joined the meeting.",
                "context_info": "This is a quarterly sales review meeting. We'll be discussing Q3 results and Q4 forecasts. The team missed their targets by 15%.",
                "enable_tools": True,
                "webhook_url": "https://example.com/meetingbaas/webhook",
                "extra": {"company": "ACME Corp", "meeting_purpose": "Weekly sync"},
            }
        }


class JoinResponse(BaseModel):
    """Response model for a bot joining a meeting"""

    bot_id: str = Field(
        ...,
        description="The MeetingBaas bot ID used for API operations with MeetingBaas",
    )


class LeaveResponse(BaseModel):
    """Response model for a bot leaving a meeting"""

    ok: bool


class LeaveBotRequest(BaseModel):
    """Request model for making a bot leave a meeting"""

    bot_id: Optional[str] = Field(
        None,
        description="The MeetingBaas bot ID to remove from the meeting. This will also close the WebSocket connection made through Pipecat by this bot.",
    )


class PersonaImageRequest(BaseModel):
    """Request model for generating persona images."""
    prompt: str


class PersonaImageResponse(BaseModel):
    """Response model for generated persona images."""
    image_url: str = Field(..., description="URL of the generated image")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Models for MeetingBaas Webhook Responses

class WordItem(BaseModel):
    """Single word in meeting transcript with timing"""
    start: float
    end: float
    word: str


class TranscriptSegment(BaseModel):
    """Segment of transcript by a single speaker"""
    speaker: str
    words: List[WordItem]


class MeetingCompletedData(BaseModel):
    """Data returned when a meeting is completed"""
    bot_id: str
    mp4: str  # Pre-signed S3 URL (valid for 2 hours)
    speakers: List[str]
    transcript: List[TranscriptSegment]


class MeetingFailedData(BaseModel):
    """Data returned when a meeting fails"""
    bot_id: str
    error: str


class MeetingStatusData(BaseModel):
    """Data for status change events"""
    bot_id: str
    status: Dict[str, Any]


class MeetingWebhookEvent(BaseModel):
    """Webhook event from MeetingBaas"""
    event: str  # "complete", "failed", or "bot.status_change"
    data: Dict[str, Any]  # Will parse this based on event type
