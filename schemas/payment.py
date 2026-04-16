from pydantic import BaseModel


class CheckoutSessionCreate(BaseModel):
    plan: str     # 'light' | 'basic' | 'advanced'
    billing: str  # 'monthly' | 'yearly'


class CheckoutSessionOut(BaseModel):
    url: str


class BillingPortalOut(BaseModel):
    url: str
