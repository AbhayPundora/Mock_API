import math
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import or_, and_, cast, func, Text

from src.database.core import DbSession, verify_api_key, limiter
from src.models.models import Person, Organization

router = APIRouter()


# ── Request models (mirrors real Apollo params) ───────────────────────────────

class PeopleSearchRequest(BaseModel):
    # partial match on job title e.g. ["CTO", "VP Engineering"]
    person_titles: list[str] = []
    # exact org IDs
    organization_ids: list[str] = []
    # strict org HQ location e.g. ["Bengaluru", "Karnataka", "India"]
    organization_locations: list[str] = []
    # strict person's own location
    person_locations: list[str] = []
    # exact seniority values e.g. ["c_suite", "vp", "director"]
    person_seniorities: list[str] = []
    # keyword search across name/title/headline
    q_keywords: Optional[str] = None
    # org employee range e.g. ["1000,5000"]
    organization_num_employees_ranges: list[str] = []
    # person function e.g. ["engineering", "sales", "marketing"]
    person_functions: list[str] = []
    # industry filter — exact match
    organization_industry_tag_ids: list[str] = []
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _obfuscate_last_name(last_name: str) -> str:
    if not last_name or len(last_name) <= 2:
        return last_name
    return last_name[:2] + "***" + last_name[-1]


def _person_to_search_result(person: Person) -> dict:
    """Minimal shape — no email or phone, mirrors mixed_people/search."""
    org = person.organization
    return {
        "id": person.id,
        "first_name": person.first_name,
        "last_name_obfuscated": _obfuscate_last_name(person.last_name or ""),
        "title": person.title,
        "headline": person.headline,
        "seniority": person.seniority,
        "departments": person.departments or [],
        "functions": person.functions or [],
        "city": person.city,
        "state": person.state,
        "country": person.country,
        "last_refreshed_at": person.last_refreshed_at,
        "has_email": person.has_email,
        "has_city": bool(person.city),
        "has_state": bool(person.state),
        "has_country": bool(person.country),
        "has_direct_phone": person.has_direct_phone or "Yes",
        "organization": {
            "id": org.id if org else None,
            "name": org.name if org else None,
            "primary_domain": org.primary_domain if org else None,
            "industry": org.industry if org else None,
            "estimated_num_employees": org.estimated_num_employees if org else None,
            "city": org.city if org else None,
            "state": org.state if org else None,
            "country": org.country if org else None,
            "logo_url": org.logo_url if org else None,
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
    """Full shape — includes email and phone, mirrors people/match."""
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
@limiter.limit("30/minute")
def search_people(
    request: Request,
    body: PeopleSearchRequest,
    db: DbSession,
    _: str = Depends(verify_api_key),
):
    """
    POST /api/v1/mixed_people/search
    All active filters are ANDed. Within multi-value filters, values are ORed.
    No email or phone returned — use /people/match for enrichment.
    """
    query = db.query(Person)

    # ── exact org IDs ──────────────────────────────────────────────────────────
    if body.organization_ids:
        query = query.filter(Person.organization_id.in_(body.organization_ids))

    # ── title — partial match (Apollo also does partial on titles) ─────────────
    if body.person_titles:
        title_filters = [
            Person.title.ilike(f"%{t.strip()}%")
            for t in body.person_titles
        ]
        query = query.filter(or_(*title_filters))

    # ── seniority — exact match ────────────────────────────────────────────────
    if body.person_seniorities:
        query = query.filter(
            Person.seniority.in_([s.lower().strip() for s in body.person_seniorities])
        )

    # ── person functions — exact match inside JSON array ──────────────────────
    if body.person_functions:
        func_filters = [
            cast(Person.functions, Text).ilike(f"%\"{f.lower().strip()}\"%")
            for f in body.person_functions
        ]
        query = query.filter(or_(*func_filters))

    # ── person's own location — strict equals ─────────────────────────────────
    if body.person_locations:
        ploc_filters = []
        for loc in body.person_locations:
            loc_lower = loc.lower().strip()
            ploc_filters.append(
                or_(
                    func.lower(Person.city) == loc_lower,
                    func.lower(Person.state) == loc_lower,
                    func.lower(Person.country) == loc_lower,
                )
            )
        query = query.filter(or_(*ploc_filters))

    # ── org HQ location — strict equals (join required) ───────────────────────
    needs_org_join = bool(
        body.organization_locations
        or body.organization_num_employees_ranges
        or body.organization_industry_tag_ids
    )
    if needs_org_join:
        query = query.join(Organization, Person.organization_id == Organization.id)

    if body.organization_locations:
        loc_filters = []
        for loc in body.organization_locations:
            loc_lower = loc.lower().strip()
            loc_filters.append(
                or_(
                    func.lower(Organization.city) == loc_lower,
                    func.lower(Organization.state) == loc_lower,
                    func.lower(Organization.country) == loc_lower,
                )
            )
        query = query.filter(or_(*loc_filters))

    # ── org employee range ─────────────────────────────────────────────────────
    if body.organization_num_employees_ranges:
        range_filters = []
        for r in body.organization_num_employees_ranges:
            parts = r.split(",")
            if len(parts) == 2:
                try:
                    min_e = int(parts[0].strip()) if parts[0].strip() else 0
                    max_e = int(parts[1].strip()) if parts[1].strip() else 9_999_999
                    range_filters.append(
                        and_(
                            Organization.estimated_num_employees >= min_e,
                            Organization.estimated_num_employees <= max_e,
                        )
                    )
                except ValueError:
                    pass
        if range_filters:
            query = query.filter(or_(*range_filters))

    # ── org industry — exact match ─────────────────────────────────────────────
    if body.organization_industry_tag_ids:
        industry_lower = [i.lower().strip() for i in body.organization_industry_tag_ids]
        query = query.filter(
            func.lower(Organization.industry).in_(industry_lower)
        )

    # ── keyword search — name, title, headline ─────────────────────────────────
    if body.q_keywords:
        kw = f"%{body.q_keywords.strip()}%"
        query = query.filter(
            or_(
                Person.name.ilike(kw),
                Person.title.ilike(kw),
                Person.headline.ilike(kw),
            )
        )

    # ── pagination ─────────────────────────────────────────────────────────────
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
            "total_pages": math.ceil(total / per_page) if total else 0,
        },
    }


@router.post("/api/v1/people/match")
@limiter.limit("20/minute")
def enrich_person(
    request: Request,
    body: PeopleMatchRequest,
    db: DbSession,
    _: str = Depends(verify_api_key),
):
    """
    POST /api/v1/people/match
    Strict lookup in priority order — same as real Apollo enrichment.
    Returns null person if nothing found.
    """
    person = None

    # 1. Apollo ID — most reliable, exact match
    if body.id:
        person = db.query(Person).filter(Person.id == body.id).first()

    # 2. Email — exact match
    if not person and body.email:
        person = db.query(Person).filter(
            func.lower(Person.email) == body.email.lower().strip()
        ).first()

    # 3. LinkedIn URL — exact match
    if not person and body.linkedin_url:
        person = db.query(Person).filter(
            func.lower(Person.linkedin_url) == body.linkedin_url.lower().strip()
        ).first()

    # 4. Name + org name — partial name match but must be same org
    if not person and body.name and body.organization_name:
        org = db.query(Organization).filter(
            Organization.name.ilike(f"%{body.organization_name.strip()}%")
        ).first()
        if org:
            person = db.query(Person).filter(
                Person.organization_id == org.id,
                Person.name.ilike(f"%{body.name.strip()}%"),
            ).first()

    # 5. Name + domain — partial name match but must be same org domain
    if not person and body.name and body.domain:
        clean_domain = body.domain.lower().strip().lstrip("www.")
        org = db.query(Organization).filter(
            func.lower(Organization.primary_domain) == clean_domain
        ).first()
        if org:
            person = db.query(Person).filter(
                Person.organization_id == org.id,
                Person.name.ilike(f"%{body.name.strip()}%"),
            ).first()

    # 6. First + last name — exact both, last resort
    if not person and body.first_name and body.last_name:
        person = db.query(Person).filter(
            func.lower(Person.first_name) == body.first_name.lower().strip(),
            func.lower(Person.last_name) == body.last_name.lower().strip(),
        ).first()

    if not person:
        return {"person": None, "request_id": None}

    return {
        "person": _person_to_enriched(person),
        "request_id": hash(person.id) % 10**18,
    }
