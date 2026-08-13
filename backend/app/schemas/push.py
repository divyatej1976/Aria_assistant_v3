from pydantic import BaseModel, Field


class PushSubscriptionRequest(BaseModel):
    endpoint: str = Field(min_length=1, max_length=1000)
    p256dh: str = Field(min_length=1, max_length=1000)
    auth: str = Field(min_length=1, max_length=500)


class PushSubscriptionResponse(BaseModel):
    id: str
    endpoint: str
    created_at: str
