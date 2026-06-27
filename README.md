# Apollo Mock API

Dummy Apollo API that mirrors real Apollo endpoints. Data served from PostgreSQL.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/mixed_companies/search` | Search organizations |
| GET | `/api/v1/organizations/{id}` | Get full org details |
| POST | `/api/v1/mixed_people/search` | Search people |
| POST | `/api/v1/people/match` | Enrich a person |
| GET | `/health` | Health check |

All endpoints require `x-api-key` header (any non-empty value works).

---

## Run locally with Docker

```bash
# Start DB + API
docker-compose up -d

# Seed the database with 10 Indian companies + people
docker-compose --profile seed up seed

# API is now running at http://localhost:8000
# Docs at http://localhost:8000/docs
```

---

## Deploy to Railway (free)

1. Push this folder to a GitHub repo
2. Go to https://railway.app → New Project → Deploy from GitHub
3. Select your repo
4. Add a PostgreSQL plugin: **+ New** → **Database** → **PostgreSQL**
5. Set environment variable:
   ```
   DATABASE_URL = ${{Postgres.DATABASE_URL}}
   ```
6. Deploy — Railway auto-detects the Dockerfile
7. After deploy, run seed via Railway shell:
   ```bash
   python -m src.seed
   ```

---

## Test the API

```bash
# Search companies in India
curl -X POST https://your-app.railway.app/api/v1/mixed_companies/search \
  -H "x-api-key: any-key" \
  -H "Content-Type: application/json" \
  -d '{"organization_locations": ["India"], "per_page": 5}'

# Get org detail
curl https://your-app.railway.app/api/v1/organizations/org_freshworks_001 \
  -H "x-api-key: any-key"

# Search people by title
curl -X POST https://your-app.railway.app/api/v1/mixed_people/search \
  -H "x-api-key: any-key" \
  -H "Content-Type: application/json" \
  -d '{"person_titles": ["CTO", "CEO"], "organization_locations": ["India"]}'

# Enrich a person
curl -X POST https://your-app.railway.app/api/v1/people/match \
  -H "x-api-key: any-key" \
  -H "Content-Type: application/json" \
  -d '{"id": "person_fw_001"}'
```

---

## Point your service at this mock

In your `.env`:
```env
APOLLO_API_KEY=any-key-works
```

In your Apollo client config, change the base URL to:
```
https://your-app.railway.app
```
