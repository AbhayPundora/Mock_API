import math
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import or_, and_, cast, func
from sqlalchemy.dialects.postgresql import JSONB

from src.database.core import DbSession, verify_api_key, limiter
from src.models.models import Organization

router = APIRouter()


# ── Request model (mirrors real Apollo params) ────────────────────────────────

class OrganizationSearchRequest(BaseModel):
    # exact org IDs
    organization_ids: list[str] = []
    # exact domain match e.g. ["freshworks.com", "zoho.com"]
    q_organization_domains_list: list[str] = []
    # partial name search
    q_organization_name: Optional[str] = None
    # keyword tags — ALL must match (AND logic like real Apollo)
    q_organization_keyword_tags: list[str] = []
    # industry — exact match against industry field (case-insensitive)
    organization_industry_tag_ids: list[str] = []
    # location — exact city, state OR country (not partial substring)
    organization_locations: list[str] = []
    organization_not_locations: list[str] = []
    # employee range e.g. ["1000,5000"]
    organization_num_employees_ranges: list[str] = []
    # tech UIDs — ANY match (OR logic)
    currently_using_any_of_technology_uids: list[str] = []
    # funding stage — exact match e.g. ["Series B", "Series C"]
    organization_latest_funding_stage_cd: list[str] = []
    # revenue range e.g. {"min": 1000000, "max": 500000000}
    revenue_range: Optional[dict] = None
    page: int = 1
    per_page: int = 25


# ── Helpers ───────────────────────────────────────────────────────────────────

def _location_matches(value: str, loc_filter: str) -> bool:
    """
    Strict location matching — the stored field must equal the filter value
    (case-insensitive), not just contain it.
    e.g. filter="Pune" matches city="Pune" but NOT state="Maharashtra"
    """
    return func.lower(value) == loc_filter.lower()


def _org_to_search_result(org: Organization) -> dict:
    """Minimal shape returned by mixed_companies/search."""
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
        "industry": org.industry,
        "estimated_num_employees": org.estimated_num_employees,
        "city": org.city,
        "state": org.state,
        "country": org.country,
        "latest_funding_stage": org.latest_funding_stage,
        "owned_by_organization_id": None,
        "intent_strength": None,
        "show_intent": True,
        "has_intent_signal_account": False,
        "intent_signal_account": None,
    }


def _org_to_full_detail(org: Organization) -> dict:
    """Full shape returned by GET /organizations/{id}."""
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
        "employee_metrics": org.employee_metrics or [],
        "show_intent": False,
        "detail_view_loaded": True,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/api/v1/mixed_companies/search")
@limiter.limit("30/minute")
def search_organizations(
    request: Request,
    body: OrganizationSearchRequest,
    db: DbSession,
    _: str = Depends(verify_api_key),
):
    """
    POST /api/v1/mixed_companies/search
    All active filters are ANDed together (same as real Apollo).
    Within a multi-value filter (e.g. multiple locations), values are ORed.
    Empty filter list = that filter is ignored.
    """
    query = db.query(Organization)

    # ── exact org IDs ──────────────────────────────────────────────────────────
    if body.organization_ids:
        query = query.filter(Organization.id.in_(body.organization_ids))

    # ── exact domain match ─────────────────────────────────────────────────────
    # Real Apollo strips www., @, etc. — we match primary_domain exactly
    if body.q_organization_domains_list:
        clean_domains = [d.lower().strip().lstrip("www.") for d in body.q_organization_domains_list]
        query = query.filter(
            or_(
                func.lower(Organization.primary_domain).in_(clean_domains)
            )
        )

    # ── name — partial match (Apollo also does partial) ────────────────────────
    if body.q_organization_name:
        query = query.filter(
            Organization.name.ilike(f"%{body.q_organization_name.strip()}%")
        )

    # ── keyword tags — ALL tags must appear in keywords (AND, not OR) ──────────
    # Real Apollo treats multiple keyword tags as AND
    for kw in body.q_organization_keyword_tags:
        query = query.filter(
            cast(Organization.keywords, JSONB).contains(
                cast([kw.lower().strip()], JSONB)
            )
        )

    # ── industry — accepts both numeric Apollo tag IDs and plain name strings ──
    # Real Apollo uses numeric IDs. The mock DB stores lowercase name strings.
    # This map translates IDs → names so both work transparently.
    APOLLO_INDUSTRY_ID_MAP = {
        "6780": "financial services",
        "6783": "banking",
        "6787": "insurance",
        "6852": "hospital & health care",
        "6861": "pharmaceuticals",
        "6926": "information technology & services",
        "6930": "computer software",
        "6942": "internet",
        "6990": "retail",
        "6991": "consumer goods",
    }
    if body.organization_industry_tag_ids:
        # translate any numeric IDs to names, pass through plain strings as-is
        resolved = [
            APOLLO_INDUSTRY_ID_MAP.get(tag.strip(), tag.strip().lower())
            for tag in body.organization_industry_tag_ids
        ]
        query = query.filter(
            func.lower(Organization.industry).in_(resolved)
        )

    # ── funding stage — exact match ────────────────────────────────────────────
    if body.organization_latest_funding_stage_cd:
        query = query.filter(
            Organization.latest_funding_stage.in_(
                body.organization_latest_funding_stage_cd
            )
        )

    # ── location — strict: city OR state OR country must equal the value ───────
    # Real Apollo matches HQ location exactly, not partial substring.
    # e.g. "Pune" only matches city=Pune, not state=Maharashtra
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
        # multiple locations = OR (any HQ matches)
        query = query.filter(or_(*loc_filters))

    # ── not locations — strict exclusion ──────────────────────────────────────
    if body.organization_not_locations:
        for loc in body.organization_not_locations:
            loc_lower = loc.lower().strip()
            query = query.filter(
                and_(
                    func.lower(Organization.city) != loc_lower,
                    func.lower(Organization.state) != loc_lower,
                    func.lower(Organization.country) != loc_lower,
                )
            )

    # ── employee range — inclusive, multiple ranges are ORed ──────────────────
    if body.organization_num_employees_ranges:
        range_filters = []
        for r in body.organization_num_employees_ranges:
            parts = r.split(",")
            if len(parts) == 2:
                try:
                    min_e = int(parts[0]) if parts[0].strip() else 0
                    max_e = int(parts[1]) if parts[1].strip() else 9_999_999
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

    # ── tech UIDs — ANY match (OR), checks uid field inside JSON array ─────────
    if body.currently_using_any_of_technology_uids:
        tech_filters = [
            cast(Organization.current_technologies, JSONB).contains(
                cast([{"uid": uid.lower().strip()}], JSONB)
            )
            for uid in body.currently_using_any_of_technology_uids
        ]
        query = query.filter(or_(*tech_filters))

    # ── revenue range — inclusive ──────────────────────────────────────────────
    if body.revenue_range:
        min_rev = body.revenue_range.get("min")
        max_rev = body.revenue_range.get("max")
        if min_rev is not None:
            query = query.filter(Organization.annual_revenue >= float(min_rev))
        if max_rev is not None:
            query = query.filter(Organization.annual_revenue <= float(max_rev))

    # ── pagination ─────────────────────────────────────────────────────────────
    total = query.count()
    page = max(1, body.page)
    per_page = min(100, max(1, body.per_page))
    offset = (page - 1) * per_page
    orgs = query.offset(offset).limit(per_page).all()

    # ── breadcrumbs (mirrors Apollo response shape) ────────────────────────────
    breadcrumbs = []
    for r in body.organization_num_employees_ranges:
        breadcrumbs.append({
            "label": "# Employees",
            "signal_field_name": "organization_num_employees_ranges",
            "value": r,
            "display_name": r.replace(",", "–"),
        })
    for loc in body.organization_locations:
        breadcrumbs.append({
            "label": "Company Locations",
            "signal_field_name": "organization_locations",
            "value": loc,
            "display_name": loc,
        })
    for ind in body.organization_industry_tag_ids:
        breadcrumbs.append({
            "label": "Industry",
            "signal_field_name": "organization_industry_tag_ids",
            "value": ind,
            "display_name": ind,
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
            "total_pages": math.ceil(total / per_page) if total else 0,
        },
        "accounts": [],
        "organizations": [_org_to_search_result(o) for o in orgs],
        "model_ids": [o.id for o in orgs],
        "num_fetch_result": None,
        "derived_params": None,
    }


@router.get("/api/v1/organizations/{org_id}")
@limiter.limit("60/minute")
def get_organization(
    request: Request,
    org_id: str,
    db: DbSession,
    _: str = Depends(verify_api_key),
):
    """GET /api/v1/organizations/{id} — full org details."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail=f"Organization {org_id} not found")

    return {"organization": _org_to_full_detail(org)}