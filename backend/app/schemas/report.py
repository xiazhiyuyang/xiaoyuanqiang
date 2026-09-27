from pydantic import BaseModel, Field


REPORT_REASONS = {
    "spam": "垃圾广告",
    "porn": "色情低俗",
    "abuse": "辱骂/人身攻击",
    "violence": "暴力血腥",
    "fraud": "诈骗/虚假信息",
    "privacy": "泄露隐私",
    "illegal": "违法违规",
    "other": "其他",
}


class ReportCreate(BaseModel):
    target_type: str = Field(..., pattern="^(post|comment|user|message)$")
    target_id: int
    reason: str = Field(..., max_length=50)
    detail: str | None = Field(None, max_length=500)


class ReportHandle(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    ban_user: bool = False
    remark: str | None = Field(None, max_length=200)
