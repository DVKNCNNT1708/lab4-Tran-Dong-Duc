# RUN_LOCAL.md - Huong dan chay Lab 04

Huong dan nay dung cho Lab 04 docker hoa **Smart Campus Analytics API** dua tren contract va Postman Collection cua Lab 03.

## 1. Cai dependencies

```bash
npm install
```

## 2. Build Docker image

```bash
docker build -t fit4110/analytics:lab04 .
```

## 3. Run container

```bash
docker run --rm \
  --name fit4110-analytics-lab04 \
  -p 8000:8000 \
  --env-file .env.example \
  fit4110/analytics:lab04
```

Mo terminal khac va kiem tra health:

```bash
curl http://localhost:8000/health
```

Ket qua mong doi:

```json
{
  "status": "ok",
  "service": "analytics",
  "time": "2026-05-25T10:00:00+00:00"
}
```

## 4. Chay Newman tren container

```bash
npm run test:local
```

Report sinh tai:

```text
reports/newman-lab04-local.xml
reports/newman-lab04-local.html
```

## 5. Dung container

```bash
docker stop fit4110-analytics-lab04
```

Lenh nhanh:

```bash
make build
make run
make test-docker
make stop
```
