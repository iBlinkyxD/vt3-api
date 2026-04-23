from pydantic import BaseModel


class CheckoutSessionCreate(BaseModel):
    plan: str     # 'light' | 'basic' | 'advanced'
    billing: str  # 'monthly' | 'yearly'


class CheckoutSessionOut(BaseModel):
    url: str


class BillingPortalOut(BaseModel):
    url: str


class ConnectStatusOut(BaseModel):
    connected: bool


class FundItemCheckout(BaseModel):
    item_id: int
    quantity: int = 1
    founder_public_id: str
    return_url: str  # public funding page URL to redirect after payment


class FundItemCheckoutOut(BaseModel):
    url: str
