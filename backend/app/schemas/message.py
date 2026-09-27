from datetime import datetime
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    target_user_id: int = Field(..., description="对方用户ID")


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: int
    peer_id: int
    peer_nickname: str
    peer_avatar: str | None = None
    last_content: str | None = None
    last_sender_id: int | None = None
    unread_count: int = 0
    last_message_at: datetime
