import math
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import or_

from src.database.core import DbSession, verify_api_key
from src.models.models import Person, Organization

router = APIRouter()


# ── Request models ────────────────────────────────────────────────────────────

class PeopleSearchRequest(BaseModel):
    person_titles: list[str] = []
    organization_ids: list[str] = []
    organization_locations: list[str] = []
    person_locations: list[str] = []
    person_seniorities: list[str] = []
    q_keywords: Optional[str] = None
    organization_num_employees_ranges: list[str] = []
    page: int = 1
    per_page: int = 25


class PeopleMatchRequest(BaseModel):
    id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    organization_name: Optional[str] = None
    domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    reveal_personal_emails: bool = False
    reveal_phone_number: bool = False


def _obfuscate_last_name(last_name: str) -> str:
    """Turn 'Zheng' into 'Zh***g'"""
    if not last_name or len(last_name) <= 2:
        return last_name
    return last_name[:2] + "***" + last_name[-1]


def _person_to_search_result(person: Person) -> dict:
    """Return person in mixed_people/search shape — no email/phone."""
    org = person.organization
    return {
        "id": person.id,
        "first_name": person.first_name,
        "last_name_obfuscated": _obfuscate_last_name(person.last_name or ""),
        "title": person.title,
        "last_refreshed_at": person.last_refreshed_at,
        "has_email": person.has_email,
        "has_city": bool(person.city),
        "has_state": bool(person.state),
        "has_country": bool(person.country),
        "has_direct_phone": person.has_direct_phone or "Yes",
        "organization": {
            "name": org.name if org else None,
            "has_industry": bool(org and org.industry),
            "has_phone": bool(org and org.phone),
            "has_city": bool(org and org.city),
            "has_state": bool(org and org.state),
            "has_country": bool(org and org.country),
            "has_zip_code": bool(org and org.postal_code),
            "has_revenue": bool(org and org.annual_revenue),
            "has_employee_count": bool(org and org.estimated_num_employees),
        } if org else None,
    }


def _person_to_enriched(person: Person) -> dict:
    """Return person in people/match shape — full details including email/phone."""
    org = person.organization
    return {
        "id": person.id,
        "first_name": person.first_name,
        "last_name": person.last_name,
        "name": person.name,
        "linkedin_url": person.linkedin_url,
        "title": person.title,
        "email_status": person.email_status or "verified",
        "photo_url": person.photo_url,
        "twitter_url": person.twitter_url,
        "github_url": person.github_url,
        "facebook_url": None,
        "extrapolated_email_confidence": None,
        "headline": person.headline,
        "email": person.email,
        "organization_id": person.organization_id,
        "employment_history": person.employment_history or [],
        "state": person.state,
        "city": person.city,
        "country": person.country,
        "revealed_for_current_team": True,
        "organization": {
            "id": org.id,
            "name": org.name,
            "website_url": org.website_url,
            "linkedin_url": org.linkedin_url,
            "primary_domain": org.primary_domain,
            "industry": org.industry,
            "estimated_num_employees": org.estimated_num_employees,
            "city": org.city,
            "state": org.state,
            "country": org.country,
            "annual_revenue": org.annual_revenue,
            "annual_revenue_printed": org.annual_revenue_printed,
            "logo_url": org.logo_url,
            "keywords": org.keywords or [],
            "technology_names": org.technology_names or [],
            "current_technologies": org.current_technologies or [],
            "total_funding": org.total_funding,
            "total_funding_printed": org.total_funding_printed,
            "latest_funding_stage": org.latest_funding_stage,
        } if org else None,
        "is_likely_to_engage": True,
        "intent_strength": None,
        "show_intent": False,
        "departments": person.departments or [],
        "subdepartments": person.subdepartments or [],
        "functions": person.functions or [],
        "seniority": person.seniority,
        "contact": {
            "id": f"contact_{person.id}",
            "first_name": person.first_name,
            "last_name": person.last_name,
            "name": person.name,
            "email": person.email,
            "sanitized_phone": (person.phone_numbers or [{}])[0].get("sanitized_number") if person.phone_numbers else None,
            "phone_numbers": person.phone_numbers or [],
            "organization_name": org.name if org else None,
            "title": person.title,
            "linkedin_url": person.linkedin_url,
            "email_status": person.email_status or "verified",
            "is_likely_to_engage": True,
        },
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/api/v1/mixed_people/search")
def search_people(
    body: PeopleSearchRequest,
    db: DbSession,
    _: str = Depends(verify_api_key),
):
    """POST /api/v1/mixed_people/search — no email/phone returned."""

    query = db.query(Person)

    # filter by org IDs
    if body.organization_ids:
        query = query.filter(Person.organization_id.in_(body.organization_ids))

    # filter by job title (partial match on any title)
    if body.person_titles:
        title_filters = [
            Person.title.ilike(f"%{t}%")
            for t in body.person_titles
        ]
        query = query.filter(or_(*title_filters))

    # filter by seniority
    if body.person_seniorities:
        query = query.filter(Person.seniority.in_(body.person_seniorities))

    # filter by location (join with org for org HQ location)
    if body.organization_locations:
        query = query.join(Organization, Person.organization_id == Organization.id)
        loc_filters = [
            or_(
                Organization.country.ilike(f"%{loc}%"),
                Organization.city.ilike(f"%{loc}%"),
                Organization.state.ilike(f"%{loc}%"),
            )
            for loc in body.organization_locations
        ]
        query = query.filter(or_(*loc_filters))

    total = query.count()
    page = max(1, body.page)
    per_page = min(100, max(1, body.per_page))
    offset = (page - 1) * per_page
    people = query.offset(offset).limit(per_page).all()

    return {
        "total_entries": total,
        "people": [_person_to_search_result(p) for p in people],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_entries": total,
            "total_pages": math.ceil(total / per_page),
        },
    }


@router.post("/api/v1/people/match")
def enrich_person(
    body: PeopleMatchRequest,
    db: DbSession,
    _: str = Depends(verify_api_key),
):
    """POST /api/v1/people/match — full enrichment with email + phone."""

    person = None

    # find by Apollo ID first (most reliable)
    if body.id:
        person = db.query(Person).filter(Person.id == body.id).first()

    # fallback: find by email
    if not person and body.email:
        person = db.query(Person).filter(Person.email == body.email).first()

    # fallback: find by linkedin
    if not person and body.linkedin_url:
        person = db.query(Person).filter(
            Person.linkedin_url == body.linkedin_url
        ).first()

    # fallback: find by name + domain
    if not person and body.name and body.domain:
        org = db.query(Organization).filter(
            Organization.primary_domain.ilike(f"%{body.domain}%")
        ).first()
        if org:
            person = db.query(Person).filter(
                Person.organization_id == org.id,
                Person.name.ilike(f"%{body.name}%"),
            ).first()

    if not person:
        return {"person": None, "request_id": None}

    return {
        "person": _person_to_enriched(person),
        "request_id": hash(person.id) % 10**18,
    }
