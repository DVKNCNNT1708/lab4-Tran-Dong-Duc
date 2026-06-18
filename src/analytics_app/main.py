import os
from collections import Counter
from http import HTTPStatus
from datetime import date, datetime, timezone
from enum import Enum
from typing import Annotated, Dict, List, Literal, Optional, Union
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


SERVICE_NAME = os.getenv("SERVICE_NAME", "analytics")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "2.0.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")


app = FastAPI(
    title="FIT4110 Lab 04 - Smart Campus Analytics Service",
    version=SERVICE_VERSION,
    description="Dockerized Analytics API aligned with the Lab 03 OpenAPI/Postman contract.",
)


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int = Field(..., ge=400, le=599)
    detail: str
    instance: Optional[str] = None


class HealthStatus(BaseModel):
    status: Literal["ok"]
    service: str
    time: str


class IngestAccepted(BaseModel):
    status: Literal["ACCEPTED"]
    acceptedAt: str


class SourceType(str, Enum):
    access = "access"
    camera = "camera"
    core_business = "core-business"
    iot = "iot"


class StrictEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AccessIngestEvent(StrictEvent):
    sourceType: Literal["access"]
    eventId: UUID
    gateId: str
    decision: Literal["ALLOW", "DENY"]
    occurredAt: datetime
    cardId: Optional[str] = None
    direction: Optional[Literal["IN", "OUT"]] = None


class CameraIngestEvent(StrictEvent):
    sourceType: Literal["camera"]
    detectionId: UUID
    detectionType: Literal["PERSON", "VEHICLE", "UNKNOWN_OBJECT"]
    confidence: float = Field(..., ge=0, le=1)
    cameraId: str
    occurredAt: datetime
    trackingId: Optional[str] = None


class CoreBusinessIngestEvent(StrictEvent):
    sourceType: Literal["core-business"]
    businessEventId: UUID
    eventType: Literal[
        "VISION_DETECTION",
        "ACCESS_DENIED",
        "UNAUTHORIZED_ACCESS",
        "SECURITY_INTRUSION",
        "NOTIFICATION_FAILURE",
    ]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    status: Literal["OPEN", "RESOLVED", "FAILED", "IGNORED"]
    occurredAt: datetime
    gateId: Optional[str] = None
    cameraId: Optional[str] = None


class IotIngestEvent(StrictEvent):
    sourceType: Literal["iot"]
    deviceId: str
    metric: Literal["temperature", "humidity", "occupancy", "power"]
    value: float
    occurredAt: datetime
    unit: Optional[str] = None


IngestEvent = Annotated[
    Union[AccessIngestEvent, CameraIngestEvent, CoreBusinessIngestEvent, IotIngestEvent],
    Field(discriminator="sourceType"),
]


class AnalyticsSummary(BaseModel):
    totalEvents: int
    totalAlerts: int
    generatedAt: str
    denyRate: float = 0
    averageConfidence: float = 0
    topCamera: Optional[str] = None


class DashboardCard(BaseModel):
    key: str
    label: str
    value: float
    unit: Optional[str] = None


class DashboardResponse(BaseModel):
    generatedAt: str
    cards: List[DashboardCard]


EVENTS: List[Dict] = []


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_problem(
    *,
    status_code: int,
    title: str,
    detail: str,
    instance: Optional[str] = None,
    problem_type: str = "about:blank",
) -> Dict:
    problem = {
        "type": problem_type,
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance:
        problem["instance"] = instance
    return problem


def http_status_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP Error"


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    problem = exc.detail if isinstance(exc.detail, dict) else build_problem(
        status_code=exc.status_code,
        title=http_status_title(exc.status_code),
        detail=str(exc.detail),
        instance=str(request.url.path),
    )

    problem.setdefault("status", exc.status_code)
    problem.setdefault("title", http_status_title(exc.status_code))
    problem.setdefault("type", "about:blank")
    problem.setdefault("detail", "Request failed")
    problem.setdefault("instance", str(request.url.path))

    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        media_type="application/problem+json",
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(item) for item in first_error.get("loc", []))
    message = first_error.get("msg", "Request validation error")
    detail = f"{location}: {message}" if location else message

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=build_problem(
            status_code=status.HTTP_400_BAD_REQUEST,
            title="Bad Request",
            detail=detail,
            instance=str(request.url.path),
            problem_type="https://smart-campus.local/problems/validation-error",
        ),
        media_type="application/problem+json",
    )


def verify_bearer_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Missing Authorization header",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )

    if authorization != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=build_problem(
                status_code=status.HTTP_401_UNAUTHORIZED,
                title="Unauthorized",
                detail="Invalid bearer token",
                problem_type="https://smart-campus.local/problems/unauthorized",
            ),
        )


def is_alert(event: Dict) -> bool:
    source_type = event.get("sourceType")
    if source_type == "access":
        return event.get("decision") == "DENY"
    if source_type == "camera":
        return float(event.get("confidence", 0)) >= 0.85
    if source_type == "core-business":
        return event.get("severity") in {"HIGH", "CRITICAL"} and event.get("status") == "OPEN"
    if source_type == "iot":
        return event.get("metric") == "temperature" and float(event.get("value", 0)) >= 70
    return False


def summarize_events(source_type: Optional[SourceType] = None) -> AnalyticsSummary:
    items = EVENTS
    if source_type:
        items = [event for event in items if event.get("sourceType") == source_type.value]

    access_events = [event for event in items if event.get("sourceType") == "access"]
    deny_events = [event for event in access_events if event.get("decision") == "DENY"]
    camera_events = [event for event in items if event.get("sourceType") == "camera"]

    confidence_values = [float(event.get("confidence", 0)) for event in camera_events]
    camera_counts = Counter(event.get("cameraId") for event in camera_events if event.get("cameraId"))

    return AnalyticsSummary(
        totalEvents=len(items),
        totalAlerts=sum(1 for event in items if is_alert(event)),
        generatedAt=now_iso(),
        denyRate=(len(deny_events) / len(access_events)) if access_events else 0,
        averageConfidence=(sum(confidence_values) / len(confidence_values))
        if confidence_values
        else 0,
        topCamera=camera_counts.most_common(1)[0][0] if camera_counts else None,
    )


@app.get("/health", response_model=HealthStatus)
def health() -> HealthStatus:
    return HealthStatus(status="ok", service=SERVICE_NAME, time=now_iso())


@app.post(
    "/ingest",
    response_model=IngestAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_bearer_token)],
    responses={
        400: {"model": ProblemDetails},
        401: {"model": ProblemDetails},
        500: {"model": ProblemDetails},
    },
)
def ingest_event(payload: IngestEvent) -> IngestAccepted:
    EVENTS.append(payload.model_dump(mode="json"))
    return IngestAccepted(status="ACCEPTED", acceptedAt=now_iso())


@app.get(
    "/analytics/summary",
    response_model=AnalyticsSummary,
    dependencies=[Depends(verify_bearer_token)],
    responses={400: {"model": ProblemDetails}, 401: {"model": ProblemDetails}},
)
def get_analytics_summary(
    fromDate: date = Query(...),
    toDate: date = Query(...),
    sourceType: Optional[SourceType] = Query(default=None),
) -> AnalyticsSummary:
    if fromDate > toDate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_problem(
                status_code=status.HTTP_400_BAD_REQUEST,
                title="Bad Request",
                detail="fromDate must be before or equal to toDate",
                problem_type="https://smart-campus.local/problems/invalid-date-range",
            ),
        )

    return summarize_events(sourceType)


@app.get(
    "/dashboard",
    response_model=DashboardResponse,
    dependencies=[Depends(verify_bearer_token)],
    responses={401: {"model": ProblemDetails}},
)
def get_dashboard() -> DashboardResponse:
    summary = summarize_events()
    return DashboardResponse(
        generatedAt=summary.generatedAt,
        cards=[
            DashboardCard(
                key="total-events",
                label="Total events",
                value=summary.totalEvents,
            ),
            DashboardCard(
                key="total-alerts",
                label="Total alerts",
                value=summary.totalAlerts,
            ),
            DashboardCard(
                key="deny-rate",
                label="Deny rate",
                value=round(summary.denyRate, 4),
                unit="ratio",
            ),
            DashboardCard(
                key="average-confidence",
                label="Average confidence",
                value=round(summary.averageConfidence, 4),
                unit="ratio",
            ),
        ],
    )
