from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True, index=True)
    phone = Column(String)

    password = Column(String)
    google_linked = Column(Boolean, default=False)

    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

    verification_code = Column(String, nullable=True)
    verification_expires = Column(DateTime, nullable=True)

    pending_email = Column(String, nullable=True)
    email_change_token = Column(String, nullable=True)
    email_change_expires = Column(DateTime, nullable=True)
    email_change_cancel_token = Column(String, nullable=True)

    session_version = Column(Integer, default=1)

    role = Column(String)

    public_id = Column(String(8), unique=True, nullable=True, index=True)
    avatar_url = Column(String, nullable=True)
    bio = Column(String, nullable=True)

    company_id = Column(Integer, ForeignKey("companies.id"))

    # Stripe billing
    stripe_customer_id  = Column(String, nullable=True, unique=True)
    stripe_connect_id   = Column(String, nullable=True, unique=True)  # Stripe Connect Express account
    subscription_plan   = Column(String, nullable=True)          # 'light' | 'basic' | 'advanced'
    subscription_status = Column(String, default="inactive")     # 'inactive' | 'trialing' | 'active' | 'past_due' | 'canceled'
    subscription_id     = Column(String, nullable=True)          # Stripe subscription ID

    company = relationship("Company", back_populates="users")
    opp_cost_investors = relationship("OppCostInvestor", back_populates="user", cascade="all, delete-orphan")