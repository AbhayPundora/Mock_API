"""
Seed script — generates 50 diverse Indian companies + 150 people using Faker.
Covers varied industries, cities, tech stacks, funding stages and employee sizes
so filters return meaningfully different results.
Run standalone: python -m src.seed
"""
import random
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faker import Faker
from src.database.core import engine, SessionLocal
from src.models.models import Base, Organization, Person

fake = Faker("en_IN")
random.seed(42)  # reproducible data

# ── Lookup tables ──────────────────────────────────────────────────────────────

INDUSTRIES = [
    ("information technology & services", ["it services", "cloud", "consulting", "devops", "artificial intelligence", "ai", "cloud migration", "gcc", "global capability centre"]),
    ("computer software", ["saas", "devops", "crm", "erp", "cloud", "artificial intelligence", "ai", "cloud migration"]),
    ("financial services", ["financial services", "fintech", "payments", "banking", "insurance", "artificial intelligence", "ai", "gcc"]),
    ("internet", ["ecommerce", "e-commerce", "marketplace", "platform", "artificial intelligence", "ai", "cloud migration"]),
    ("retail", ["retail", "supply chain", "omnichannel", "d2c", "ecommerce", "e-commerce", "artificial intelligence"]),
    ("consumer goods", ["consumer goods", "fmcg", "d2c", "retail", "supply chain", "artificial intelligence"]),
    ("e-commerce", ["ecommerce", "e-commerce", "marketplace", "d2c", "retail", "artificial intelligence", "logistics"]),
    ("healthcare", ["healthcare", "healthtech", "telemedicine", "ehr", "artificial intelligence", "ai", "diagnostics", "cloud migration"]),
    ("education", ["edtech", "lms", "upskilling", "artificial intelligence", "ai", "mooc"]),
    ("logistics & supply chain", ["logistics", "last-mile", "fleet", "supply chain", "artificial intelligence", "cloud migration"]),
    ("media & entertainment", ["ott", "streaming", "content", "adtech", "artificial intelligence"]),
    ("real estate", ["proptech", "realestate", "smart home", "iot", "artificial intelligence"]),
    ("banking", ["banking", "neobank", "payments", "fintech", "artificial intelligence", "gcc", "global capability centre"]),
    ("insurance", ["insurance", "insurtech", "fintech", "artificial intelligence", "ai"]),
    ("hospital & health care", ["hospital", "healthtech", "ehr", "telemedicine", "artificial intelligence", "cloud migration"]),
    ("pharmaceuticals", ["pharmaceuticals", "pharma", "biotech", "drug discovery", "artificial intelligence", "ai"]),
]

CITIES = [
    ("Bengaluru", "Karnataka"),
    ("Mumbai", "Maharashtra"),
    ("Chennai", "Tamil Nadu"),
    ("Pune", "Maharashtra"),
    ("Hyderabad", "Telangana"),
    ("Delhi", "Delhi"),
    ("Gurugram", "Haryana"),
    ("Noida", "Uttar Pradesh"),
    ("Kolkata", "West Bengal"),
    ("Ahmedabad", "Gujarat"),
]

TECH_POOL = [
    {"uid": "aws", "name": "AWS", "category": "Cloud Services"},
    {"uid": "azure", "name": "Azure", "category": "Cloud Services"},
    {"uid": "gcp", "name": "GCP", "category": "Cloud Services"},
    {"uid": "python", "name": "Python", "category": "Frameworks and Programming Languages"},
    {"uid": "java", "name": "Java", "category": "Frameworks and Programming Languages"},
    {"uid": "go", "name": "Go", "category": "Frameworks and Programming Languages"},
    {"uid": "node", "name": "Node.js", "category": "Frameworks and Programming Languages"},
    {"uid": "react", "name": "React", "category": "Frameworks and Programming Languages"},
    {"uid": "kubernetes", "name": "Kubernetes", "category": "DevOps"},
    {"uid": "terraform", "name": "Terraform", "category": "DevOps"},
    {"uid": "datadog", "name": "Datadog", "category": "Observability"},
    {"uid": "newrelic", "name": "New Relic", "category": "Observability"},
    {"uid": "prometheus", "name": "Prometheus", "category": "Observability"},
    {"uid": "redis", "name": "Redis", "category": "Databases"},
    {"uid": "postgres", "name": "PostgreSQL", "category": "Databases"},
    {"uid": "mongodb", "name": "MongoDB", "category": "Databases"},
    {"uid": "kafka", "name": "Kafka", "category": "Data Streaming"},
    {"uid": "spark", "name": "Spark", "category": "Data Engineering"},
    {"uid": "ai", "name": "AI", "category": "Other"},
    {"uid": "ml", "name": "ML", "category": "Other"},
    {"uid": "selenium", "name": "Selenium", "category": "Testing"},
    {"uid": "salesforce", "name": "Salesforce", "category": "CRM"},
]

FUNDING_STAGES = [
    "Pre-Seed", "Seed", "Series A", "Series B", "Series C",
    "Series D", "Series E", "Series F", "Series G", "IPO",
    "Bootstrapped", "Public",
]

SENIORITIES = ["founder", "c_suite", "vp", "director", "manager", "senior", "mid"]

TITLES_BY_SENIORITY = {
    "founder": ["CEO & Founder", "Co-Founder & CEO", "Founder & CTO", "Founder"],
    "c_suite": ["CEO", "CTO", "CFO", "COO", "CMO", "CPO", "CHRO"],
    "vp": ["VP Engineering", "VP Sales", "VP Product", "VP Marketing", "VP Operations"],
    "director": ["Director of Engineering", "Director of Sales", "Director of Product", "Director of Finance"],
    "manager": ["Engineering Manager", "Product Manager", "Sales Manager", "Marketing Manager"],
    "senior": ["Senior Software Engineer", "Senior Data Engineer", "Senior DevOps Engineer", "Senior Analyst"],
    "mid": ["Software Engineer", "Data Analyst", "DevOps Engineer", "QA Engineer", "Business Analyst"],
}

DEPARTMENTS_BY_SENIORITY = {
    "founder": ["c_suite"],
    "c_suite": ["c_suite"],
    "vp": ["leadership"],
    "director": ["leadership"],
    "manager": ["management"],
    "senior": ["engineering", "sales", "marketing", "finance", "operations"],
    "mid": ["engineering", "sales", "marketing", "finance", "operations"],
}

# ── Hardcoded well-known companies (keep original 10) ─────────────────────────

KNOWN_ORGS = [
    {
        "id": "org_freshworks_001", "name": "Freshworks",
        "website_url": "https://www.freshworks.com",
        "linkedin_url": "https://www.linkedin.com/company/freshworks-inc",
        "twitter_url": "https://twitter.com/freshworks",
        "facebook_url": "https://facebook.com/freshworks",
        "phone": "+91 44 6667 8000", "sanitized_phone": "+914466678000",
        "primary_phone": {"number": "+91 44 6667 8000", "source": "Scraped", "sanitized_number": "+914466678000"},
        "languages": ["English", "Hindi"], "alexa_ranking": 3200, "linkedin_uid": "2152688",
        "founded_year": 2010, "logo_url": "https://logo.clearbit.com/freshworks.com",
        "primary_domain": "freshworks.com", "industry": "computer software",
        "estimated_num_employees": 7000,
        "keywords": ["crm", "customer support", "saas", "cloud", "ai", "helpdesk", "itsm"],
        "industries": ["computer software"], "secondary_industries": ["information technology & services"],
        "raw_address": "2950 S Delaware St Suite 201, San Mateo, California, United States",
        "street_address": "2950 S Delaware St Suite 201", "city": "Chennai",
        "state": "Tamil Nadu", "postal_code": "600113", "country": "India",
        "short_description": "Freshworks makes it fast and easy for businesses to delight their customers and employees.",
        "annual_revenue": 596000000, "annual_revenue_printed": "596M",
        "total_funding": 484000000, "total_funding_printed": "484M",
        "latest_funding_round_date": "2021-09-22T00:00:00.000+00:00", "latest_funding_stage": "IPO",
        "funding_events": [{"id": "fe_fw_001", "date": "2021-09-22T00:00:00.000+00:00", "type": "IPO", "investors": "Public Market", "amount": "1B", "currency": "$"}],
        "technology_names": ["AWS", "Python", "React", "Kubernetes", "AI"],
        "current_technologies": [{"uid": "aws", "name": "AWS", "category": "Cloud Services"}, {"uid": "python", "name": "Python", "category": "Frameworks and Programming Languages"}, {"uid": "react", "name": "React", "category": "Frameworks and Programming Languages"}, {"uid": "kubernetes", "name": "Kubernetes", "category": "DevOps"}, {"uid": "ai", "name": "AI", "category": "Other"}],
    },
    {
        "id": "org_razorpay_001", "name": "Razorpay",
        "website_url": "https://razorpay.com",
        "linkedin_url": "https://www.linkedin.com/company/razorpay",
        "twitter_url": "https://twitter.com/Razorpay", "facebook_url": "https://facebook.com/razorpay",
        "phone": "+91 80 6160 6161", "sanitized_phone": "+918061606161",
        "primary_phone": {"number": "+91 80 6160 6161", "source": "Scraped", "sanitized_number": "+918061606161"},
        "languages": ["English", "Hindi"], "alexa_ranking": 1800, "linkedin_uid": "5151167",
        "founded_year": 2014, "logo_url": "https://logo.clearbit.com/razorpay.com",
        "primary_domain": "razorpay.com", "industry": "financial services",
        "estimated_num_employees": 3500,
        "keywords": ["fintech", "payments", "saas", "cloud", "ai", "banking", "api"],
        "industries": ["financial services"], "secondary_industries": ["computer software"],
        "raw_address": "SJR Cyber Laskar, Hosur Road, Bengaluru, Karnataka 560068, India",
        "street_address": "SJR Cyber Laskar", "city": "Bengaluru",
        "state": "Karnataka", "postal_code": "560068", "country": "India",
        "short_description": "Razorpay is a full-stack financial solutions company for Indian businesses.",
        "annual_revenue": 480000000, "annual_revenue_printed": "480M",
        "total_funding": 741500000, "total_funding_printed": "741.5M",
        "latest_funding_round_date": "2021-12-19T00:00:00.000+00:00", "latest_funding_stage": "Series F",
        "funding_events": [{"id": "fe_rp_001", "date": "2021-12-19T00:00:00.000+00:00", "type": "Series F", "investors": "Lone Pine Capital", "amount": "375M", "currency": "$"}],
        "technology_names": ["AWS", "Python", "Go", "Kubernetes", "AI", "PostgreSQL", "Redis"],
        "current_technologies": [{"uid": "aws", "name": "AWS", "category": "Cloud Services"}, {"uid": "python", "name": "Python", "category": "Frameworks and Programming Languages"}, {"uid": "kubernetes", "name": "Kubernetes", "category": "DevOps"}, {"uid": "redis", "name": "Redis", "category": "Databases"}, {"uid": "ai", "name": "AI", "category": "Other"}],
    },
    {
        "id": "org_swiggy_001", "name": "Swiggy",
        "website_url": "https://www.swiggy.com",
        "linkedin_url": "https://www.linkedin.com/company/swiggy-in",
        "twitter_url": "https://twitter.com/Swiggy", "facebook_url": "https://facebook.com/swiggy.in",
        "phone": "+91 80 6746 6000", "sanitized_phone": "+918067466000",
        "primary_phone": {"number": "+91 80 6746 6000", "source": "Scraped", "sanitized_number": "+918067466000"},
        "languages": ["English", "Hindi"], "alexa_ranking": 900, "linkedin_uid": "5284414",
        "founded_year": 2014, "logo_url": "https://logo.clearbit.com/swiggy.com",
        "primary_domain": "swiggy.com", "industry": "internet",
        "estimated_num_employees": 5000,
        "keywords": ["food delivery", "cloud kitchen", "ai", "machine learning", "logistics", "platform"],
        "industries": ["internet"], "secondary_industries": ["consumer goods"],
        "raw_address": "3rd Floor, RmZ Ecoworld, Bengaluru, Karnataka 560103, India",
        "street_address": "3rd Floor, RmZ Ecoworld", "city": "Bengaluru",
        "state": "Karnataka", "postal_code": "560103", "country": "India",
        "short_description": "Swiggy is India's leading on-demand delivery platform.",
        "annual_revenue": 1200000000, "annual_revenue_printed": "1.2B",
        "total_funding": 3625000000, "total_funding_printed": "3.6B",
        "latest_funding_round_date": "2024-11-13T00:00:00.000+00:00", "latest_funding_stage": "IPO",
        "funding_events": [{"id": "fe_sw_001", "date": "2024-11-13T00:00:00.000+00:00", "type": "IPO", "investors": "Public Market", "amount": "1.35B", "currency": "$"}],
        "technology_names": ["AWS", "Python", "Go", "Kubernetes", "AI", "Kafka", "Redis"],
        "current_technologies": [{"uid": "aws", "name": "AWS", "category": "Cloud Services"}, {"uid": "python", "name": "Python", "category": "Frameworks and Programming Languages"}, {"uid": "kubernetes", "name": "Kubernetes", "category": "DevOps"}, {"uid": "ai", "name": "AI", "category": "Other"}, {"uid": "kafka", "name": "Kafka", "category": "Data Streaming"}],
    },
]


# ── Faker-generated companies ──────────────────────────────────────────────────

def _make_org(idx: int) -> dict:
    """Generate one realistic Indian company.
    Uses a grid distribution so every industry+city combo gets coverage.
    """
    industry_entry = INDUSTRIES[idx % len(INDUSTRIES)]
    industry, kw_pool = industry_entry

    # distribute cities independently of industry so combos overlap
    city, state = CITIES[idx % len(CITIES)]

    emp_bands = [75, 150, 300, 600, 1200, 2500, 4000, 6000, 15000, 50000]
    employees = emp_bands[idx % len(emp_bands)] + random.randint(0, 50)

    stage = FUNDING_STAGES[idx % len(FUNDING_STAGES)]
    revenue_base = employees * random.randint(5000, 50000)
    funding_base = revenue_base * random.uniform(0.5, 3.0)

    techs = random.sample(TECH_POOL, k=random.randint(3, 7))
    slug = fake.slug()
    domain = f"{slug}.io"
    org_id = f"org_gen_{idx:03d}"

    keywords = random.sample(kw_pool + ["ai", "cloud", "saas", "api"], k=min(5, len(kw_pool) + 4))

    return {
        "id": org_id,
        "name": fake.company(),
        "website_url": f"https://{domain}",
        "linkedin_url": f"https://www.linkedin.com/company/{slug}",
        "twitter_url": f"https://twitter.com/{slug}",
        "facebook_url": f"https://facebook.com/{slug}",
        "phone": fake.phone_number(),
        "sanitized_phone": f"+91{random.randint(7000000000, 9999999999)}",
        "primary_phone": {"number": fake.phone_number(), "source": "Scraped", "sanitized_number": f"+91{random.randint(7000000000, 9999999999)}"},
        "languages": random.sample(["English", "Hindi", "Tamil", "Telugu", "Kannada", "Marathi"], k=random.randint(1, 3)),
        "alexa_ranking": random.randint(500, 50000),
        "linkedin_uid": str(random.randint(100000, 9999999)),
        "founded_year": random.randint(2005, 2023),
        "logo_url": f"https://logo.clearbit.com/{domain}",
        "primary_domain": domain,
        "industry": industry,
        "estimated_num_employees": employees,
        "keywords": keywords,
        "industries": [industry],
        "secondary_industries": [INDUSTRIES[(idx + 1) % len(INDUSTRIES)][0]],
        "raw_address": f"{fake.street_address()}, {city}, {state}, India",
        "street_address": fake.street_address(),
        "city": city,
        "state": state,
        "postal_code": str(random.randint(100000, 999999)),
        "country": "India",
        "short_description": fake.catch_phrase() + ". " + fake.bs().capitalize() + ".",
        "annual_revenue": float(revenue_base),
        "annual_revenue_printed": f"{revenue_base // 1_000_000}M" if revenue_base >= 1_000_000 else f"{revenue_base // 1000}K",
        "total_funding": float(funding_base) if stage not in ("Bootstrapped",) else 0.0,
        "total_funding_printed": f"{int(funding_base) // 1_000_000}M" if funding_base >= 1_000_000 else "Bootstrapped",
        "latest_funding_round_date": f"202{random.randint(0,4)}-{random.randint(1,12):02d}-01T00:00:00.000+00:00" if stage not in ("Bootstrapped", "Public") else None,
        "latest_funding_stage": stage,
        "funding_events": [],
        "technology_names": [t["name"] for t in techs],
        "current_technologies": techs,
    }


def _make_person(idx: int, org_id: str, org_name: str, domain: str) -> dict:
    """Generate one realistic person for a given org."""
    seniority = SENIORITIES[idx % len(SENIORITIES)]
    title = random.choice(TITLES_BY_SENIORITY[seniority])
    dept = random.choice(DEPARTMENTS_BY_SENIORITY[seniority])
    first = fake.first_name()
    last = fake.last_name()
    email_local = f"{first.lower()}.{last.lower()}{random.randint(1,99)}"

    return {
        "id": f"person_gen_{idx:04d}",
        "organization_id": org_id,
        "first_name": first,
        "last_name": last,
        "last_name_obfuscated": last[:2] + "***" + last[-1] if len(last) > 2 else last,
        "name": f"{first} {last}",
        "title": title,
        "email": f"{email_local}@{domain}",
        "email_status": random.choice(["verified", "verified", "verified", "likely"]),
        "photo_url": None,
        "linkedin_url": f"https://www.linkedin.com/in/{first.lower()}-{last.lower()}-{random.randint(100,999)}",
        "headline": f"{title} at {org_name}",
        "city": fake.city(),
        "state": random.choice([c[1] for c in CITIES]),
        "country": "India",
        "seniority": seniority,
        "departments": [dept],
        "subdepartments": [dept],
        "functions": [dept.replace("_", " ")],
        "has_email": True,
        "has_direct_phone": "Yes",
        "last_refreshed_at": f"2025-{random.randint(1,6):02d}-01T00:00:00.000+00:00",
        "phone_numbers": [{"raw_number": fake.phone_number(), "sanitized_number": f"+91{random.randint(7000000000, 9999999999)}", "type": "mobile", "position": 0, "status": "valid_number", "dnc_status": None}],
        "employment_history": [{"_id": f"eh_gen_{idx:04d}", "current": True, "organization_id": org_id, "organization_name": org_name, "start_date": f"20{random.randint(15,23):02d}-01-01", "title": title, "id": f"eh_gen_{idx:04d}", "key": f"eh_gen_{idx:04d}"}],
    }


# ── Seed function ──────────────────────────────────────────────────────────────

def seed():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # clear existing data
        db.query(Person).delete()
        db.query(Organization).delete()
        db.commit()
        print("Cleared existing data.")

        # seed known orgs
        all_orgs = []
        for org_data in KNOWN_ORGS:
            org = Organization(**org_data)
            db.add(org)
            all_orgs.append(org_data)

        # generate 47 more orgs (total = 50)
        for i in range(47):
            org_data = _make_org(i)
            org = Organization(**org_data)
            db.add(org)
            all_orgs.append(org_data)

        db.commit()
        print(f"Seeded {len(all_orgs)} organizations.")

        # seed 3 people per known org
        person_idx = 0
        for org_data in KNOWN_ORGS:
            for j in range(3):
                p_data = _make_person(
                    person_idx,
                    org_data["id"],
                    org_data["name"],
                    org_data["primary_domain"],
                )
                db.add(Person(**p_data))
                person_idx += 1

        # seed 3 people per generated org
        for org_data in all_orgs[len(KNOWN_ORGS):]:
            for j in range(3):
                p_data = _make_person(
                    person_idx,
                    org_data["id"],
                    org_data["name"],
                    org_data["primary_domain"],
                )
                db.add(Person(**p_data))
                person_idx += 1

        db.commit()
        print(f"Seeded {person_idx} people.")
        print("✅ Seed complete!")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
