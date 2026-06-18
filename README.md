# FIT4110 Lab 04 - Docker Packaging

**Hoc phan:** FIT4110 - Dich vu ket noi va Cong nghe nen tang  
**Buoi 4:** Dong goi service voi Docker  
**Service:** Smart Campus Analytics API  
**Repo nen Lab 03:** `lab-03-api-contract-testing-PDMtruong2k5`

Lab 04 tiep tuc tu Lab 03. Thay vi chi chay contract/Postman tren mock server, repo nay dong goi Analytics service thanh Docker image, chay container, roi chay lai Newman tren container de lay evidence.

```text
OpenAPI Contract
-> Service that
-> Dockerfile
-> Docker Image
-> Docker Container
-> Postman/Newman chay lai tren container
-> Evidence
```

## API duoc dong goi

Contract chinh:

```text
contracts/analytics.openapi.yaml
```

Endpoint chinh:

```text
GET  /health
POST /ingest
GET  /analytics/summary
GET  /dashboard
```

Payload happy path tu Lab 03:

```json
{
  "sourceType": "camera",
  "detectionId": "550e8400-e29b-41d4-a716-446655440000",
  "detectionType": "PERSON",
  "confidence": 0.95,
  "cameraId": "CAM-01",
  "occurredAt": "2026-05-25T10:00:00Z"
}
```

Boundary dung trong bai:

```text
camera.confidence: 0 den 1
```

## Cau truc repo

```text
lab4-PDMtruong2k5/
├── Dockerfile
├── .dockerignore
├── .env.example
├── RUN_LOCAL.md
├── Makefile
├── package.json
├── requirements.txt
├── src/
│   └── analytics_app/
│       ├── __init__.py
│       └── main.py
├── contracts/
│   ├── analytics.openapi.yaml
│   └── ai-vision.openapi.yaml
├── postman/
│   ├── collections/
│   │   └── Analytics_API.postman_collection.json
│   └── environments/
│       ├── Analytics Local.postman_environment.json
│       └── Analytics Mock.postman_environment.json
├── reports/
└── .github/
    └── workflows/
        └── docker-newman.yml
```

## Chuan bi

Can cai:

- Git
- Docker Desktop hoac Docker Engine
- Node.js 20.x LTS
- npm
- Python 3.11+ neu chay local khong dung Docker

```bash
npm install
```

Kiem tra:

```bash
docker --version
node --version
npx newman --version
npx prism --version
```

## Chay local khong dung Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn analytics_app.main:app --app-dir src --host 0.0.0.0 --port 8000
```

Kiem tra:

```bash
curl http://localhost:8000/health
```

## Build va run bang Docker

```bash
docker build -t fit4110/analytics:lab04 .
docker run --rm \
  --name fit4110-analytics-lab04 \
  -p 8000:8000 \
  --env-file .env.example \
  fit4110/analytics:lab04
```

Container chay bang non-root user va co `HEALTHCHECK` goi `GET /health`.

## Chay Newman tren container

Sau khi container dang chay:

```bash
npm run test:local
```

Report Lab 04 sinh tai:

```text
reports/newman-lab04-local.xml
reports/newman-lab04-local.html
```

Collection kiem tra:

- Functional: health, summary, dashboard, ingest happy path
- Auth: missing token, invalid token
- Negative: missing required field, invalid payload type
- Boundary: confidence = 1 accepted, confidence > 1 rejected
- Error response: `ProblemDetails`

## Lenh nhanh

```bash
make install
make lint
make build
make run
make test-docker
make stop
```

## Dieu kien hoan thanh

- `Dockerfile` build duoc image.
- Image run duoc container.
- `GET /health` tra `200`.
- Service chay bang non-root user trong container.
- Co `.dockerignore`.
- Co `.env.example`.
- Co `RUN_LOCAL.md`.
- Newman pass tren container.
- Co test functional, auth, negative, boundary.
- Error response tra dang `ProblemDetails`.
- Co report trong `reports/`.

Tag goi y:

```bash
docker tag fit4110/analytics:lab04 ghcr.io/<owner>/team-analytics:v0.1.0-team-analytics
```

## Artifact can nop

```text
Dockerfile
.dockerignore
.env.example
RUN_LOCAL.md
contracts/analytics.openapi.yaml
postman/collections/Analytics_API.postman_collection.json
postman/environments/Analytics Local.postman_environment.json
reports/newman-lab04-local.xml
reports/newman-lab04-local.html
anh chup /health hoac log container
tag image da push len registry
```
