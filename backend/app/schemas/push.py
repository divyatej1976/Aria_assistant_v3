from pydantic import BaseModel, Field


class PushSubscriptionRequest(BaseModel):
    endpoint: str = Field(min_length=1, max_length=1000)
    p256dh: str = Field(min_length=1, max_length=1000)
    auth: str = Field(min_length=1, max_length=500)


class PushUnsubscribeRequest(BaseModel):
    # Keys are not needed to remove a subscription, and the browser may no
    # longer have them at teardown time. Deletion is owner-scoped.
    endpoint: str = Field(min_length=1, max_length=1000)


class PushSubscriptionResponse(BaseModel):
    id: str
    endpoint: str
    created_at: str
