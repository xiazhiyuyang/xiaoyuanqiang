from datetime import datetime
from pydantic import BaseModel, Field



class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    parent_id: int | None = None
    reply_to_user_id: int | None = None


class CommentAuthor(BaseModel):
    id: int
    nickname: str
    avatar: str | None

    model_config = {"from_attributes": True}


class CommentResponse(BaseModel):
    id: int
    post_id: int
    content: str
    author: CommentAuthor | None = None
    author_name: str | None = None
    parent_id: int | None
    reply_to_user_id: int | None
    like_count: int
    is_liked: bool = False
    created_at: datetime
    replies: list["CommentResponse"] = []

    model_config = {"from_attributes": True}


CommentResponse.model_rebuild()
