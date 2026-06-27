import math
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import or_, and_, cast
from sqlalchemy.dialects.postgresql import JSONB

from src.database.core import DbSession, verify_api_key
from src.models.models import Organization

router = APIRouter()


# ── Request model ─────────────────────────────────────────────────────────────

class OrganizationSearchRequest(BaseModel):
    q_organization_domains_list: list[str] = []
    organization_num_employees_ranges: list[str] = []
    organization_locations: list[str] = []
    organization_not_locations: list[str] = []
    q_organization_keyword_tags: list[str] = []
    q_organization_name: Optional[str] = None
    organization_ids: list[str] = []
    currently_using_any_of_technology_uids: list[str] = []
    revenue_range: Optional[dict] = None
    page: int = 1
    per_page: int = 25


def _obfuscate_last_name(last_name: str) -> str:
    """Turn 'Zheng' into 'Zh***g'"""
    if not last_name or len(last_name) <= 2:
        return last_name
    return last_name[:2] + "***" + last_name[-1]


def _org_to_search_result(org: Organization) -> dict:
    """Return org in mixed_companies/search shape — minimal fields."""
    return {
        "id": org.id,
        "name": org.name,
        "website_url": org.website_url,
        "blog_url": org.blog_url,
        "angellist_url": None,
        "linkedin_url": org.linkedin_url,
        "twitter_url": org.twitter_url,
        "facebook_url": org.facebook_url,
        "primary_phone": org.primary_phone or {},
        "languages": org.languages or [],
        "alexa_ranking": org.alexa_ranking,
        "phone": org.phone,
        "linkedin_uid": org.linkedin_uid,
        "founded_year": org.founded_year,
        "publicly_traded_symbol": org.publicly_traded_symbol,
        "publicly_traded_exchange": org.publicly_traded_exchange,
        "logo_url": org.logo_url,
        "crunchbase_url": org.crunchbase_url,
        "primary_domain": org.primary_domain,
        "sanitized_phone": org.sanitized_phone,
        "owned_by_organization_id": None,
        "intent_strength": None,
        "show_intent": True,
        "has_intent_signal_account": False,
        "intent_signal_account": None,
    }


def _org_to_full_detail(org: Organization) -> dict:
    """Return org in GET /organizations/{id} shape — full fields."""
    return {
        "id": org.id,
        "name": org.name,
        "website_url": org.website_url,
        "blog_url": org.blog_url,
        "angellist_url": None,
        "linkedin_url": org.linkedin_url,
        "twitter_url": org.twitter_url,
        "facebook_url": org.facebook_url,
        "primary_phone": org.primary_phone or {},
        "languages": org.languages or [],
        "alexa_ranking": org.alexa_ranking,
        "phone": org.phone,
        "linkedin_uid": org.linkedin_uid,
        "founded_year": org.founded_year,
        "publicly_traded_symbol": org.publicly_traded_symbol,
        "publicly_traded_exchange": org.publicly_traded_exchange,
        "logo_url": org.logo_url,
        "crunchbase_url": org.crunchbase_url,
        "primary_domain": org.primary_domain,
        "industry": org.industry,
        "estimated_num_employees": org.estimated_num_employees,
        "keywords": org.keywords or [],
        "industries": org.industries or [],
        "secondary_industries": org.secondary_industries or [],
        "snippets_loaded": True,
        "raw_address": org.raw_address,
        "street_address": org.street_address,
        "city": org.city,
        "state": org.state,
        "postal_code": org.postal_code,
        "country": org.country,
        "owned_by_organization_id": None,
        "short_description": org.short_description,
        "annual_revenue_printed": org.annual_revenue_printed,
        "annual_revenue": org.annual_revenue,
        "total_funding": org.total_funding,
        "total_funding_printed": org.total_funding_printed,
        "latest_funding_round_date": org.latest_funding_round_date,
        "latest_funding_stage": org.latest_funding_stage,
        "funding_events": org.funding_events or [],
        "technology_names": org.technology_names or [],
        "current_technologies": org.current_technologies or [],
        "show_intent": False,
        "detail_view_loaded": True,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/api/v1/mixed_companies/search")
def search_organizations(
    body: OrganizationSearchRequest,
    db: DbSession,
    _: str = Depends(verify_api_key),
):
    """POST /api/v1/mixed_companies/search — mirrors Apollo org search."""
    query = db.query(Organization)

    # filter by specific org IDs
    if body.organization_ids:
        query = query.filter(Organization.id.in_(body.organization_ids))

    # filter by domain
    if body.q_organization_domains_list:
        domain_filters = [
            Organization.primary_domain.ilike(f"%{d}%")
            for d in body.q_organization_domains_list
        ]
        query = query.filter(or_(*domain_filters))

    # filter by name
    if body.q_organization_name:
        query = query.filter(
            Organization.name.ilike(f"%{body.q_organization_name}%")
        )

    # filter by location
    if body.organization_locations:
        loc_filters = [
            or_(
                Organization.country.ilike(f"%{loc}%"),
                Organization.city.ilike(f"%{loc}%"),
                Organization.state.ilike(f"%{loc}%"),
            )
            for loc in body.organization_locations
        ]
        query = query.filter(or_(*loc_filters))

    # exclude locations
    if body.organization_not_locations:
        for loc in body.organization_not_locations:
            query = query.filter(
                and_(
                    ~Organization.country.ilike(f"%{loc}%"),
                    ~Organization.city.ilike(f"%{loc}%"),
                    ~Organization.state.ilike(f"%{loc}%"),
                )
            )

    # filter by employee count ranges e.g. ["250,1000", "5000,10000"]
    if body.organization_num_employees_ranges:
        range_filters = []
        for r in body.organization_num_employees_ranges:
            parts = r.split(",")
            if len(parts) == 2:
                min_e = int(parts[0]) if parts[0] else 0
                max_e = int(parts[1]) if parts[1] else 9999999
                range_filters.append(
                    and_(
                        Organization.estimated_num_employees >= min_e,
                        Organization.estimated_num_employees <= max_e,
                    )
                )
        if range_filters:
            query = query.filter(or_(*range_filters))

    # filter by technology UIDs — search inside the current_technologies JSON array
    if body.currently_using_any_of_technology_uids:
        tech_filters = [
            cast(Organization.current_technologies, JSONB).contains(
                cast([{"uid": uid}], JSONB)
            )
            for uid in body.currently_using_any_of_technology_uids
        ]
        query = query.filter(or_(*tech_filters))

    # filter by revenue range e.g. {"min": 1000000, "max": 500000000}
    if body.revenue_range:
        min_rev = body.revenue_range.get("min")
        max_rev = body.revenue_range.get("max")
        if min_rev is not None:
            query = query.filter(Organization.annual_revenue >= min_rev)
        if max_rev is not None:
            query = query.filter(Organization.annual_revenue <= max_rev)

    total = query.count()
    page = max(1, body.page)
    per_page = min(100, max(1, body.per_page))
    offset = (page - 1) * per_page
    orgs = query.offset(offset).limit(per_page).all()

    # build breadcrumbs from active filters
    breadcrumbs = []
    for r in body.organization_num_employees_ranges:
        breadcrumbs.append({
            "label": "# Employees",
            "signal_field_name": "organization_num_employees_ranges",
            "value": r,
            "display_name": r.replace(",", "-"),
        })
    for loc in body.organization_locations:
        breadcrumbs.append({
            "label": "Company Locations",
            "signal_field_name": "organization_locations",
            "value": loc,
            "display_name": loc,
        })

    return {
        "breadcrumbs": breadcrumbs,
        "partial_results_only": False,
        "has_join": False,
        "disable_eu_prospecting": False,
        "partial_results_limit": 10000,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_entries": total,
            "total_pages": math.ceil(total / per_page),
        },
        "accounts": [],
        "organizations": [_org_to_search_result(o) for o in orgs],
        "model_ids": [o.id for o in orgs],
        "num_fetch_result": None,
        "derived_params": None,
    }


@router.get("/api/v1/organizations/{org_id}")
def get_organization(
    org_id: str,
    db: DbSession,
    _: str = Depends(verify_api_key),
):
    """GET /api/v1/organizations/{id} — full org details."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail=f"Organization {org_id} not found")

    return {"organization": _org_to_full_detail(org)}
