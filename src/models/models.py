from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, Text, JSON, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(255), primary_key=True)  # Apollo org ID e.g. "5e66b638..."
    name = Column(String(255), nullable=False)
    website_url = Column(String(255))
    blog_url = Column(String(255))
    linkedin_url = Column(String(255))
    twitter_url = Column(String(255))
    facebook_url = Column(String(255))
    phone = Column(String(100))
    sanitized_phone = Column(String(100))
    primary_phone = Column(JSON)
    languages = Column(JSON, default=list)
    alexa_ranking = Column(Integer)
    linkedin_uid = Column(String(100))
    founded_year = Column(Integer)
    publicly_traded_symbol = Column(String(50))
    publicly_traded_exchange = Column(String(50))
    logo_url = Column(String(500))
    crunchbase_url = Column(String(255))
    primary_domain = Column(String(255))
    industry = Column(String(255))
    estimated_num_employees = Column(Integer)
    keywords = Column(JSON, default=list)
    industries = Column(JSON, default=list)
    secondary_industries = Column(JSON, default=list)
    raw_address = Column(Text)
    street_address = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(50))
    country = Column(String(100))
    short_description = Column(Text)
    annual_revenue = Column(Float)
    annual_revenue_printed = Column(String(50))
    total_funding = Column(Float)
    total_funding_printed = Column(String(50))
    latest_funding_round_date = Column(String(100))
    latest_funding_stage = Column(String(100))
    funding_events = Column(JSON, default=list)
    technology_names = Column(JSON, default=list)
    current_technologies = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    people = relationship("Person", back_populates="organization")


class Person(Base):
    __tablename__ = "people"

    id = Column(String(255), primary_key=True)  # Apollo person ID
    organization_id = Column(String(255), ForeignKey("organizations.id"), nullable=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    last_name_obfuscated = Column(String(100))  # "Zh***g" format
    name = Column(String(255))
    title = Column(String(255))
    email = Column(String(255))
    email_status = Column(String(50))
    photo_url = Column(String(500))
    linkedin_url = Column(String(255))
    twitter_url = Column(String(255))
    github_url = Column(String(255))
    headline = Column(String(500))
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    seniority = Column(String(50))
    departments = Column(JSON, default=list)
    subdepartments = Column(JSON, default=list)
    functions = Column(JSON, default=list)
    employment_history = Column(JSON, default=list)
    phone_numbers = Column(JSON, default=list)
    has_email = Column(Boolean, default=True)
    has_direct_phone = Column(String(10), default="Yes")
    last_refreshed_at = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    organization = relationship("Organization", back_populates="people")
