from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent.cleanup import CleanupCandidate, CleanupPolicy, FileUseState
from backend.app.agent.evidence import Evidence
from backend.app.agent.orchestrator import AgentOrchestrator
from backend.app.agent.planning import Planner
from backend.app.agent.rca import RCAEngine
from backend.app.agent.state_machine import TaskState, can_transition
from backend.app.api.schemas import (
    ApprovalCreate,
    ApprovalDecision,
    ConfigBaselineCreate,
    ConfigDriftRequest,
    ExecutionPreviewRequest,
    ExecutionRunRequest,
    IncidentUpdate,
    KnowledgeCreate,
    KnowledgeReview,
    LoginRequest,
    ProcessCandidateCreate,
    SettingsUpdate,
    TaskCreate,
    TaskTransition,
    ToolTestRequest,
)
from backend.app.audit.service import redact, verify_chain, write_audit
from backend.app.auth.dependencies import current_user, require_roles
from backend.app.auth.security import create_session_token, hash_token, verify_password
from backend.app.core.config import AppConfig, get_config
from backend.app.core.config_drift import detect_drift, redact_line
from backend.app.core.errors import AppError, ErrorCode
from backend.app.core.inspection_service import capture_inspection
from backend.app.db.models import (
    AgentTask,
    Approval,
    AuditEvent,
    BackupRecord,
    CleanupCandidateRecord,
    ConfigBaseline,
    EvidenceRecordModel,
    ExecutionRecord,
    GuardDecisionRecord,
    Incident,
    ProcessCandidateRecord,
    RollbackRecord,
    Setting,
    SystemSnapshot,
    TaskStep,
    ToolCallRecord,
    User,
    UserSession,
    VerificationResultRecord,
)
from backend.app.db.session import get_db
from backend.app.executor.broker import BrokerSystemctlRunner, LocalExecutionBroker
from backend.app.executor.config_update import ConfigTarget, ControlledConfigExecutor
from backend.app.executor.demo_service import demo_execution_service
from backend.app.executor.process import ControlledProcessExecutor, ProcessCandidate
from backend.app.executor.production import ControlledCleanupExecutor
from backend.app.executor.systemd import ControlledServiceExecutor
from backend.app.guardrails.approval import ApprovalTokenManager
from backend.app.guardrails.policy import PolicyEngine, canonical_arguments
from backend.app.knowledge.service import FTSKnowledgeBase
from backend.app.llm.provider import provider_from_environment
from backend.app.mcp_client.client import KylinGuardMCPClient

router = APIRouter(prefix="/api/v1")


def envelope(request: Request, data: object) -> dict[str, object]:
    config = get_config()
    return {
        "request_id": request.state.request_id,
        "data": data,
        "error": None,
        "meta": {"mode": config.mode, "is_demo": config.mode == "DEMO"},
    }


@router.get("/health")
def health(
    request: Request, config: Annotated[AppConfig, Depends(get_config)]
) -> dict[str, object]:
    return envelope(request, {"status": "ok", "service": config.name})


@router.post("/auth/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, object]:
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        write_audit(db, "AUTH_LOGIN_FAILED", {"username": body.username})
        db.commit()
        raise AppError(ErrorCode.AUTH_INVALID, "invalid credentials", 401)
    token = create_session_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
    )
    db.add(session)
    write_audit(db, "AUTH_LOGIN_SUCCEEDED", {"username": user.username}, actor_id=user.id)
    db.commit()
    return envelope(request, {"access_token": token, "token_type": "bearer", "expires_in": 28800})


@router.get("/auth/me")
def me(request: Request, user: Annotated[User, Depends(current_user)]) -> dict[str, object]:
    return envelope(
        request,
        {
            "id": user.id,
            "username": user.username,
            "roles": sorted(role.name for role in user.roles),
        },
    )


@router.post("/auth/logout")
def logout(
    request: Request,
    user: Annotated[User, Depends(current_user)],
    authorization: Annotated[str, Header()],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    token = authorization.removeprefix("Bearer ").strip()
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    if session is not None:
        session.revoked_at = datetime.now(timezone.utc)
    write_audit(db, "AUTH_LOGOUT", {}, actor_id=user.id)
    db.commit()
    return envelope(request, {"status": "logged_out"})


@router.post("/tasks", status_code=201)
def create_task(
    body: TaskCreate,
    request: Request,
    user: Annotated[User, require_roles("operator", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    config = get_config()
    requested = body.requested_mode or config.mode
    if requested != config.mode:
        raise AppError(ErrorCode.VALIDATION_ERROR, "task mode must match server mode", 422)
    task = AgentTask(user_id=user.id, goal=body.goal, mode=config.mode, state=TaskState.RECEIVED)
    db.add(task)
    db.flush()
    write_audit(
        db,
        "TASK_CREATED",
        {"goal": body.goal, "mode": config.mode},
        actor_id=user.id,
        task_id=task.id,
    )
    db.commit()
    db.refresh(task)
    return envelope(request, task_payload(task))


@router.get("/tasks")
def list_tasks(
    request: Request,
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    tasks = db.scalars(select(AgentTask).order_by(AgentTask.created_at.desc()).limit(limit)).all()
    return envelope(request, [task_payload(task) for task in tasks])


@router.get("/tasks/{task_id}")
def get_task(
    task_id: str,
    request: Request,
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    task = db.get(AgentTask, task_id)
    if task is None:
        raise AppError(ErrorCode.NOT_FOUND, "task not found", 404)
    return envelope(request, task_payload(task))


@router.post("/tasks/{task_id}/cancel")
def cancel_task(
    task_id: str,
    request: Request,
    user: Annotated[User, require_roles("operator", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    task = db.get(AgentTask, task_id)
    if task is None:
        raise AppError(ErrorCode.NOT_FOUND, "task not found", 404)
    current = TaskState(task.state)
    if not can_transition(current, TaskState.CANCELLED):
        raise AppError(
            ErrorCode.INVALID_STATE_TRANSITION,
            "task cannot be cancelled at this state",
            409,
        )
    task.state = TaskState.CANCELLED
    task.version += 1
    write_audit(
        db,
        "TASK_CANCELLED",
        {"from": current},
        actor_id=user.id,
        task_id=task.id,
    )
    db.commit()
    return envelope(request, task_payload(task))


@router.post("/tasks/{task_id}/transition")
def transition_task(
    task_id: str,
    body: TaskTransition,
    request: Request,
    user: Annotated[User, require_roles("operator", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    task = db.get(AgentTask, task_id)
    if task is None:
        raise AppError(ErrorCode.NOT_FOUND, "task not found", 404)
    current = TaskState(task.state)
    if not can_transition(current, body.target_state):
        raise AppError(
            ErrorCode.INVALID_STATE_TRANSITION,
            "invalid task state transition",
            409,
            {"from": current, "to": body.target_state},
        )
    sequence = len(task.steps) + 1
    db.add(
        TaskStep(
            task_id=task.id,
            sequence=sequence,
            from_state=current,
            to_state=body.target_state,
            reason_code=body.reason_code,
        )
    )
    task.state = body.target_state
    task.version += 1
    write_audit(
        db,
        "TASK_STATE_CHANGED",
        {"from": current, "to": body.target_state, "reason_code": body.reason_code},
        actor_id=user.id,
        task_id=task.id,
    )
    db.commit()
    db.refresh(task)
    return envelope(request, task_payload(task))


@router.get("/audit/events")
def audit_events(
    request: Request,
    _: Annotated[User, require_roles("auditor", "admin")],
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    events = db.scalars(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    ).all()
    data = [
        {
            "id": event.id,
            "task_id": event.task_id,
            "event_type": event.event_type,
            "payload": json.loads(event.payload_json),
            "created_at": event.created_at,
        }
        for event in events
    ]
    return envelope(request, data)


def task_payload(task: AgentTask) -> dict[str, object]:
    return {
        "id": task.id,
        "goal": task.goal,
        "mode": task.mode,
        "state": task.state,
        "version": task.version,
        "created_at": task.created_at,
    }


@router.get("/mcp/tools")
def mcp_tools(
    request: Request,
    _: Annotated[User, Depends(current_user)],
) -> dict[str, object]:
    client = KylinGuardMCPClient()
    return envelope(request, [tool.model_dump(mode="json") for tool in client.list_tools()])


@router.get("/mcp/health")
def mcp_health(request: Request) -> dict[str, object]:
    return envelope(request, KylinGuardMCPClient().health())


@router.post("/mcp/tools/{tool_name}/test")
def mcp_tool_test(
    tool_name: str,
    request: Request,
    _: Annotated[User, require_roles("operator", "admin")],
    body: ToolTestRequest | None = None,
) -> dict[str, object]:
    arguments = dict(body.arguments) if body else {}
    if tool_name == "service_status" and not arguments:
        arguments = {"service": "nginx"}
    result = KylinGuardMCPClient().call_tool(tool_name, arguments)
    return envelope(request, result.model_dump(mode="json"))


@router.post("/tasks/{task_id}/approvals", status_code=201)
def create_approval(
    task_id: str,
    body: ApprovalCreate,
    request: Request,
    user: Annotated[User, require_roles("operator", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    task = db.get(AgentTask, task_id)
    if task is None:
        raise AppError(ErrorCode.NOT_FOUND, "task not found", 404)
    if body.tool_name == "safe_log_cleanup" and get_config().mode == "CONTROLLED_EXECUTION":
        candidate_id = body.arguments.get("candidate_id")
        if set(body.arguments) != {"candidate_id"} or not isinstance(candidate_id, str):
            raise AppError(ErrorCode.VALIDATION_ERROR, "cleanup candidate is required", 422)
        candidate = db.get(CleanupCandidateRecord, candidate_id)
        if candidate is None or candidate.task_id != task.id or candidate.status != "ELIGIBLE":
            raise AppError(ErrorCode.VALIDATION_ERROR, "cleanup candidate is invalid", 422)
    if body.tool_name == "rollback_change" and get_config().mode == "CONTROLLED_EXECUTION":
        change_id = body.arguments.get("change_id")
        if set(body.arguments) != {"change_id"} or not isinstance(change_id, str):
            raise AppError(ErrorCode.VALIDATION_ERROR, "change id is required", 422)
        execution = db.get(ExecutionRecord, change_id)
        if execution is None or execution.task_id != task.id or execution.status != "SUCCEEDED":
            raise AppError(ErrorCode.VALIDATION_ERROR, "change cannot be rolled back", 422)
    if body.tool_name == "service_restart" and get_config().mode == "CONTROLLED_EXECUTION":
        service = body.arguments.get("service")
        allowed = get_config().controlled_execution.allowed_services
        if set(body.arguments) != {"service"} or not isinstance(service, str) or service not in allowed:
            raise AppError(ErrorCode.VALIDATION_ERROR, "service is not allowlisted", 422)
    if body.tool_name == "config_safe_update" and get_config().mode == "CONTROLLED_EXECUTION":
        target_id = body.arguments.get("target_id")
        content = body.arguments.get("content")
        allowed_targets = {
            item.target_id for item in get_config().controlled_execution.managed_configs
        }
        if (
            set(body.arguments) != {"target_id", "content"}
            or not isinstance(target_id, str)
            or target_id not in allowed_targets
            or not isinstance(content, str)
        ):
            raise AppError(ErrorCode.VALIDATION_ERROR, "config target is not allowlisted", 422)
    if body.tool_name == "terminate_process" and get_config().mode == "CONTROLLED_EXECUTION":
        candidate_id = body.arguments.get("candidate_id")
        if set(body.arguments) != {"candidate_id"} or not isinstance(candidate_id, str):
            raise AppError(ErrorCode.VALIDATION_ERROR, "process candidate is required", 422)
        process_candidate = db.get(ProcessCandidateRecord, candidate_id)
        if (
            process_candidate is None
            or process_candidate.task_id != task.id
            or process_candidate.status != "ELIGIBLE"
        ):
            raise AppError(ErrorCode.VALIDATION_ERROR, "process candidate is invalid", 422)
    decision = PolicyEngine().authorize_tool(
        user_goal=task.goal,
        tool_name=body.tool_name,
        read_only=False,
        server_mode=get_config().mode,
    )
    if not decision.allowed:
        write_audit(
            db,
            "APPROVAL_REQUEST_BLOCKED",
            {"tool_name": body.tool_name, "reason": decision.reason_code},
            actor_id=user.id,
            task_id=task.id,
        )
        db.commit()
        raise AppError(ErrorCode.RBAC_DENIED, "action is forbidden by policy", 403)
    canonical = canonical_arguments(body.arguments)
    approval = Approval(
        task_id=task.id,
        requester_id=user.id,
        tool_name=body.tool_name,
        arguments_json=canonical,
        arguments_hash=hashlib.sha256(canonical.encode()).hexdigest(),
        risk_level="L3",
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=body.expires_in),
    )
    db.add(approval)
    db.flush()
    write_audit(
        db,
        "APPROVAL_REQUESTED",
        {
            "approval_id": approval.id,
            "tool_name": body.tool_name,
            "arguments_hash": approval.arguments_hash,
        },
        actor_id=user.id,
        task_id=task.id,
    )
    db.commit()
    return envelope(request, approval_payload(approval))


@router.get("/approvals")
def list_approvals(
    request: Request,
    _: Annotated[User, require_roles("approver", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    approvals = db.scalars(select(Approval).order_by(Approval.created_at.desc()).limit(200)).all()
    return envelope(request, [approval_payload(item) for item in approvals])


@router.get("/tasks/{task_id}/approvals")
def list_task_approvals(
    task_id: str,
    request: Request,
    user: Annotated[User, require_roles("operator", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    task = db.get(AgentTask, task_id)
    if task is None:
        raise AppError(ErrorCode.NOT_FOUND, "task not found", 404)
    if "admin" not in {role.name for role in user.roles} and task.user_id != user.id:
        raise AppError(ErrorCode.RBAC_DENIED, "task approval access denied", 403)
    approvals = db.scalars(
        select(Approval).where(Approval.task_id == task_id).order_by(Approval.created_at)
    ).all()
    return envelope(request, [approval_payload(item) for item in approvals])


@router.get("/approvals/{approval_id}")
def get_approval(
    approval_id: str,
    request: Request,
    _: Annotated[User, require_roles("approver", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise AppError(ErrorCode.NOT_FOUND, "approval not found", 404)
    return envelope(request, approval_payload(approval))


@router.post("/approvals/{approval_id}/approve")
def approve(
    approval_id: str,
    body: ApprovalDecision,
    request: Request,
    user: Annotated[User, require_roles("approver", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    approval = _pending_approval(db, approval_id)
    if approval.requester_id == user.id:
        raise AppError(ErrorCode.RBAC_DENIED, "self approval is forbidden", 403)
    approval.status = "APPROVED"
    approval.approver_id = user.id
    approval.decided_at = datetime.now(timezone.utc)
    write_audit(
        db,
        "APPROVAL_APPROVED",
        {"approval_id": approval.id, "reason": body.reason},
        actor_id=user.id,
        task_id=approval.task_id,
    )
    db.commit()
    return envelope(request, approval_payload(approval))


@router.post("/approvals/{approval_id}/claim")
def claim_approval_token(
    approval_id: str,
    request: Request,
    user: Annotated[User, require_roles("operator", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise AppError(ErrorCode.NOT_FOUND, "approval not found", 404)
    if approval.requester_id != user.id or approval.status != "APPROVED":
        raise AppError(ErrorCode.RBAC_DENIED, "approved requester access is required", 403)
    remaining = int((_as_utc(approval.expires_at) - datetime.now(timezone.utc)).total_seconds())
    if remaining <= 0:
        approval.status = "EXPIRED"
        db.commit()
        raise AppError(ErrorCode.INVALID_STATE_TRANSITION, "approval expired", 409)
    arguments = json.loads(approval.arguments_json)
    token = ApprovalTokenManager(_approval_secret()).issue(
        approval.requester_id,
        approval.task_id,
        approval.tool_name,
        arguments,
        ttl=remaining,
    )
    approval.token_hash = hashlib.sha256(token.encode()).hexdigest()
    write_audit(
        db,
        "APPROVAL_TOKEN_CLAIMED",
        {"approval_id": approval.id, "token_rotated": True},
        actor_id=user.id,
        task_id=approval.task_id,
    )
    db.commit()
    data = approval_payload(approval)
    data["approval_token"] = token
    return envelope(request, data)


@router.post("/approvals/{approval_id}/reject")
def reject(
    approval_id: str,
    body: ApprovalDecision,
    request: Request,
    user: Annotated[User, require_roles("approver", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    approval = _pending_approval(db, approval_id)
    approval.status = "REJECTED"
    approval.approver_id = user.id
    approval.decided_at = datetime.now(timezone.utc)
    write_audit(
        db,
        "APPROVAL_REJECTED",
        {"approval_id": approval.id, "reason": body.reason},
        actor_id=user.id,
        task_id=approval.task_id,
    )
    db.commit()
    return envelope(request, approval_payload(approval))


def _pending_approval(db: Session, approval_id: str) -> Approval:
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise AppError(ErrorCode.NOT_FOUND, "approval not found", 404)
    if approval.status != "PENDING" or _as_utc(approval.expires_at) <= datetime.now(timezone.utc):
        raise AppError(ErrorCode.INVALID_STATE_TRANSITION, "approval is not pending", 409)
    return approval


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def approval_payload(approval: Approval) -> dict[str, object]:
    arguments = json.loads(approval.arguments_json)
    summary: dict[str, object] = {}
    for key in ("candidate_id", "service", "target_id", "change_id"):
        if key in arguments:
            summary[key] = arguments[key]
    if isinstance(arguments.get("content"), str):
        content = arguments["content"]
        summary["content_length"] = len(content.encode())
        summary["content_hash"] = hashlib.sha256(content.encode()).hexdigest()
    return {
        "id": approval.id,
        "task_id": approval.task_id,
        "tool_name": approval.tool_name,
        "arguments_hash": approval.arguments_hash,
        "risk_level": approval.risk_level,
        "status": approval.status,
        "expires_at": approval.expires_at,
        "arguments_summary": summary,
    }


@router.post("/tasks/{task_id}/run")
def run_task(
    task_id: str,
    request: Request,
    user: Annotated[User, require_roles("operator", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    task = db.get(AgentTask, task_id)
    if task is None:
        raise AppError(ErrorCode.NOT_FOUND, "task not found", 404)
    mcp = KylinGuardMCPClient()
    result = AgentOrchestrator(
        Planner(provider_from_environment(), mcp, server_mode=get_config().mode),
        mcp,
        knowledge_search=_knowledge().search_approved,
    ).run(task.goal)
    for decision in result.get("cleanup_analysis", []):
        if not isinstance(decision, dict) or not decision.get("eligible"):
            continue
        candidate = decision.get("candidate")
        if not isinstance(candidate, dict):
            continue
        candidate_id = str(candidate["candidate_id"])
        if db.get(CleanupCandidateRecord, candidate_id) is None:
            db.add(
                CleanupCandidateRecord(
                    id=candidate_id,
                    task_id=task.id,
                    path=str(candidate["path"]),
                    size_bytes=int(candidate["size_bytes"]),
                    modified_at=datetime.fromisoformat(str(candidate["modified_at"])),
                    inode=int(candidate["inode"]),
                    device=int(candidate["device"]),
                    snapshot_hash=str(candidate["snapshot_hash"]),
                )
            )
    _persist_agent_trace(db, task.id, result)
    task.state = str(result["status"])
    task.version += 1
    write_audit(
        db,
        "AGENT_RUN_COMPLETED",
        {"status": result["status"], "plan": result["plan"]},
        actor_id=user.id,
        task_id=task.id,
    )
    db.commit()
    return envelope(request, result)


def _persist_agent_trace(db: Session, task_id: str, result: dict[str, object]) -> None:
    plan = result.get("plan")
    plan_data = plan if isinstance(plan, dict) else {}
    raw_steps = plan_data.get("steps")
    steps: list[dict[str, object]] = (
        [item for item in raw_steps if isinstance(item, dict)]
        if isinstance(raw_steps, list)
        else []
    )
    raw_calls = result.get("evidence")
    calls = raw_calls if isinstance(raw_calls, list) else []
    for index, raw_call in enumerate(calls):
        if not isinstance(raw_call, dict):
            continue
        payload = raw_call.get("payload")
        safe_payload = redact(payload if isinstance(payload, dict) else {})
        step = steps[index] if index < len(steps) and isinstance(steps[index], dict) else {}
        raw_arguments = step.get("arguments")
        arguments: dict[str, object] = (
            {str(key): value for key, value in raw_arguments.items()}
            if isinstance(raw_arguments, dict)
            else {}
        )
        serialized = json.dumps(safe_payload, ensure_ascii=False, sort_keys=True, default=str)
        db.add(
            ToolCallRecord(
                task_id=task_id,
                sequence=index + 1,
                tool_name=str(raw_call.get("tool_name", "unknown")),
                arguments_hash=hashlib.sha256(canonical_arguments(arguments).encode()).hexdigest(),
                status=str(safe_payload.get("status", "UNKNOWN")),
                result_json=serialized[:262144],
                trust_label="UNTRUSTED_DATA",
            )
        )
    normalized = result.get("normalized_evidence")
    for item in normalized if isinstance(normalized, list) else []:
        if not isinstance(item, dict):
            continue
        serialized = json.dumps(redact(item), ensure_ascii=False, sort_keys=True, default=str)
        db.add(
            EvidenceRecordModel(
                id=str(item.get("evidence_id")),
                task_id=task_id,
                evidence_type=str(item.get("evidence_type", "METRIC")),
                source=str(item.get("source", "unknown")),
                payload_json=serialized[:65536],
                trust_label="UNTRUSTED_DATA",
                content_hash=hashlib.sha256(serialized.encode()).hexdigest(),
            )
        )
    chain = result.get("decision_chain")
    risk = str(plan_data.get("risk_level", "L4" if result.get("status") == "BLOCKED" else "L1"))
    for item in chain if isinstance(chain, list) else []:
        if not isinstance(item, dict):
            continue
        reason = str(item.get("reason_code", "UNKNOWN"))
        db.add(
            GuardDecisionRecord(
                task_id=task_id,
                stage=str(item.get("stage", "unknown")),
                decision="BLOCKED" if reason == "FORBIDDEN_INPUT" else "ALLOWED",
                risk_level=risk,
                reason_code=reason[:64],
                public_summary=str(item.get("summary", ""))[:1000],
            )
        )


@router.get("/cleanup/candidates")
def list_cleanup_candidates(
    request: Request,
    _: Annotated[User, require_roles("operator", "approver", "admin")],
    db: Session = Depends(get_db),
    task_id: str | None = Query(default=None, max_length=64),
) -> dict[str, object]:
    statement = select(CleanupCandidateRecord).order_by(
        CleanupCandidateRecord.created_at.desc()
    )
    if task_id is not None:
        statement = statement.where(CleanupCandidateRecord.task_id == task_id)
    candidates = db.scalars(statement.limit(200)).all()
    return envelope(
        request,
        [
            {
                "candidate_id": item.id,
                "task_id": item.task_id,
                "path": item.path,
                "size_bytes": item.size_bytes,
                "modified_at": item.modified_at,
                "snapshot_hash": item.snapshot_hash,
                "status": item.status,
                "risk_level": "L3",
                "requires_approval": True,
            }
            for item in candidates
        ],
    )


@router.post("/process-candidates", status_code=201)
def create_process_candidate(
    body: ProcessCandidateCreate,
    request: Request,
    user: Annotated[User, require_roles("operator", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if get_config().mode != "CONTROLLED_EXECUTION":
        raise AppError(ErrorCode.RBAC_DENIED, "controlled execution mode is required", 403)
    task = db.get(AgentTask, body.task_id)
    if task is None or task.mode != "CONTROLLED_EXECUTION":
        raise AppError(ErrorCode.NOT_FOUND, "controlled task not found", 404)
    try:
        candidate = _production_process_executor().create_candidate(body.pid)
    except ValueError as error:
        raise AppError(ErrorCode.VALIDATION_ERROR, "process candidate rejected", 422) from error
    record = db.get(ProcessCandidateRecord, candidate.candidate_id)
    if record is None:
        record = ProcessCandidateRecord(
            id=candidate.candidate_id,
            task_id=task.id,
            pid=candidate.pid,
            process_name=candidate.name,
            start_ticks=candidate.start_ticks,
            service=candidate.service,
        )
        db.add(record)
    write_audit(
        db,
        "PROCESS_CANDIDATE_CREATED",
        {
            "candidate_id": candidate.candidate_id,
            "pid": candidate.pid,
            "process_name": candidate.name,
            "service": candidate.service,
        },
        actor_id=user.id,
        task_id=task.id,
    )
    db.commit()
    return envelope(request, _process_candidate_payload(record))


@router.get("/process-candidates")
def list_process_candidates(
    request: Request,
    _: Annotated[User, require_roles("operator", "approver", "admin")],
    db: Session = Depends(get_db),
    task_id: str | None = Query(default=None, max_length=64),
) -> dict[str, object]:
    statement = select(ProcessCandidateRecord).order_by(
        ProcessCandidateRecord.created_at.desc()
    )
    if task_id is not None:
        statement = statement.where(ProcessCandidateRecord.task_id == task_id)
    records = db.scalars(statement.limit(200)).all()
    return envelope(request, [_process_candidate_payload(item) for item in records])


def _process_candidate_payload(record: ProcessCandidateRecord) -> dict[str, object]:
    return {
        "candidate_id": record.id,
        "task_id": record.task_id,
        "pid": record.pid,
        "process_name": record.process_name,
        "start_ticks": record.start_ticks,
        "service": record.service,
        "status": record.status,
        "risk_level": "L3",
        "requires_approval": True,
    }


@router.get("/tasks/{task_id}/events")
def task_events(
    task_id: str,
    request: Request,
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    events = db.scalars(
        select(AuditEvent).where(AuditEvent.task_id == task_id).order_by(AuditEvent.created_at)
    ).all()
    return envelope(
        request,
        [
            {
                "event_id": event.id,
                "event_type": event.event_type,
                "timestamp": event.created_at,
                "payload": json.loads(event.payload_json),
            }
            for event in events
        ],
    )


@router.get("/tasks/{task_id}/stream")
def task_stream(
    task_id: str,
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> StreamingResponse:
    events = db.scalars(
        select(AuditEvent).where(AuditEvent.task_id == task_id).order_by(AuditEvent.created_at)
    ).all()

    def generate() -> Iterator[str]:
        for event in events:
            payload = json.dumps(
                {
                    "event_id": event.id,
                    "event_type": event.event_type,
                    "timestamp": event.created_at.isoformat(),
                    "payload": json.loads(event.payload_json),
                },
                ensure_ascii=False,
            )
            yield f"id: {event.id}\nevent: task\ndata: {payload}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


def _knowledge() -> FTSKnowledgeBase:
    knowledge = FTSKnowledgeBase(Path("data/knowledge.db"))
    knowledge.initialize()
    return knowledge


@router.post("/rca/analyze")
def analyze_rca(
    evidence: list[Evidence],
    request: Request,
    _: Annotated[User, require_roles("operator", "admin")],
) -> dict[str, object]:
    candidates = RCAEngine().analyze(evidence)
    return envelope(
        request,
        {
            "candidates": [item.model_dump(mode="json") for item in candidates],
            "conclusion": "INSUFFICIENT_EVIDENCE" if not candidates else "CANDIDATES_READY",
        },
    )


@router.post("/knowledge", status_code=201)
def add_knowledge(
    body: KnowledgeCreate,
    request: Request,
    user: Annotated[User, require_roles("admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _knowledge().add(body.document_id, body.title, body.content, body.review_status)
    write_audit(
        db,
        "KNOWLEDGE_CREATED",
        {"document_id": body.document_id, "review_status": body.review_status},
        actor_id=user.id,
    )
    db.commit()
    return envelope(
        request,
        {"document_id": body.document_id, "review_status": body.review_status},
    )


@router.get("/knowledge")
def search_knowledge(
    request: Request,
    _: Annotated[User, Depends(current_user)],
    query: str = Query(min_length=1, max_length=200),
) -> dict[str, object]:
    hits = _knowledge().search(query)
    return envelope(request, [hit.__dict__ for hit in hits])


@router.put("/knowledge/{document_id}")
def review_knowledge(
    document_id: str,
    body: KnowledgeReview,
    request: Request,
    user: Annotated[User, require_roles("admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        _knowledge().review(document_id, body.review_status)
    except ValueError as error:
        raise AppError(ErrorCode.NOT_FOUND, "knowledge document not found", 404) from error
    write_audit(
        db,
        "KNOWLEDGE_REVIEWED",
        {"document_id": document_id, "review_status": body.review_status},
        actor_id=user.id,
    )
    db.commit()
    return envelope(
        request,
        {"document_id": document_id, "review_status": body.review_status},
    )


@router.get("/audit/verify")
def audit_verify(
    request: Request,
    _: Annotated[User, require_roles("auditor", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    valid, broken_event_id = verify_chain(db)
    return envelope(
        request,
        {
            "valid": valid,
            "broken_event_id": broken_event_id,
            "status": "VALID" if valid else "TAMPERED",
        },
    )


@router.get("/audit/export")
def audit_export(
    request: Request,
    _: Annotated[User, require_roles("auditor", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at, AuditEvent.id)).all()
    return envelope(
        request,
        [
            {
                "event_id": event.id,
                "task_id": event.task_id,
                "event_type": event.event_type,
                "payload": json.loads(event.payload_json),
                "previous_hash": event.previous_hash,
                "current_hash": event.current_hash,
                "timestamp": event.created_at,
            }
            for event in events
        ],
    )


def snapshot_payload(snapshot: SystemSnapshot) -> dict[str, object]:
    return {
        "id": snapshot.id,
        "source": snapshot.source,
        "payload": json.loads(snapshot.payload_json),
        "is_demo": snapshot.is_demo,
        "captured_at": snapshot.captured_at,
    }


@router.get("/system/overview")
def system_overview(
    request: Request,
    _: Annotated[User, Depends(current_user)],
) -> dict[str, object]:
    client = KylinGuardMCPClient()
    snapshot = client.call_tool("system_snapshot")
    capabilities = client.call_tool("capability_probe")
    return envelope(
        request,
        {
            "snapshot": snapshot.model_dump(mode="json"),
            "capabilities": capabilities.model_dump(mode="json"),
        },
    )


@router.post("/inspections/run", status_code=201)
def run_inspection(
    request: Request,
    user: Annotated[User, require_roles("operator", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = capture_inspection(db, actor_id=user.id)
    return envelope(
        request,
        {
            "snapshot": snapshot_payload(result.snapshot),
            "baseline": result.baseline,
            "incidents": [incident_payload(item) for item in result.incidents],
        },
    )


@router.get("/inspections")
def list_inspections(
    request: Request,
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    snapshots = db.scalars(
        select(SystemSnapshot).order_by(SystemSnapshot.captured_at.desc()).limit(200)
    ).all()
    return envelope(request, [snapshot_payload(item) for item in snapshots])


@router.get("/incidents")
def list_incidents(
    request: Request,
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    incidents = db.scalars(select(Incident).order_by(Incident.created_at.desc()).limit(200)).all()
    return envelope(
        request,
        [
            incident_payload(item)
            for item in incidents
        ],
    )


def incident_payload(item: Incident) -> dict[str, object]:
    return {
        "id": item.id,
        "snapshot_id": item.snapshot_id,
        "severity": item.severity,
        "status": item.status,
        "summary": item.summary,
        "created_at": item.created_at,
    }


@router.put("/incidents/{incident_id}")
def update_incident(
    incident_id: str,
    body: IncidentUpdate,
    request: Request,
    user: Annotated[User, require_roles("operator", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise AppError(ErrorCode.NOT_FOUND, "incident not found", 404)
    incident.status = body.status
    write_audit(
        db,
        "INCIDENT_STATUS_UPDATED",
        {"incident_id": incident.id, "status": body.status},
        actor_id=user.id,
    )
    db.commit()
    return envelope(request, incident_payload(incident))


@router.post("/config-drift/baselines", status_code=201)
def create_config_baseline(
    body: ConfigBaselineCreate,
    request: Request,
    user: Annotated[User, require_roles("admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if db.scalar(select(ConfigBaseline).where(ConfigBaseline.path_ref == body.path_ref)):
        raise AppError(ErrorCode.INVALID_STATE_TRANSITION, "baseline already exists", 409)
    redacted = "\n".join(redact_line(line) for line in body.content.splitlines())
    baseline = ConfigBaseline(
        path_ref=body.path_ref,
        content_hash=hashlib.sha256(body.content.encode()).hexdigest(),
        redacted_content=redacted,
        created_by=user.id,
    )
    db.add(baseline)
    write_audit(
        db,
        "CONFIG_BASELINE_CREATED",
        {"path_ref": body.path_ref, "content_hash": baseline.content_hash},
        actor_id=user.id,
    )
    db.commit()
    return envelope(
        request,
        {"id": baseline.id, "path_ref": baseline.path_ref, "content_hash": baseline.content_hash},
    )


@router.get("/config-drift")
def list_config_baselines(
    request: Request,
    _: Annotated[User, Depends(current_user)],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    baselines = db.scalars(select(ConfigBaseline).order_by(ConfigBaseline.created_at.desc())).all()
    return envelope(
        request,
        [
            {
                "id": item.id,
                "path_ref": item.path_ref,
                "content_hash": item.content_hash,
                "created_at": item.created_at,
            }
            for item in baselines
        ],
    )


@router.post("/config-drift/check")
def check_config_drift(
    body: ConfigDriftRequest,
    request: Request,
    _: Annotated[User, require_roles("operator", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    baseline = db.scalar(select(ConfigBaseline).where(ConfigBaseline.path_ref == body.path_ref))
    if baseline is None:
        raise AppError(ErrorCode.NOT_FOUND, "baseline not found", 404)
    redacted_current = "\n".join(redact_line(line) for line in body.current_content.splitlines())
    result = detect_drift(baseline.redacted_content, redacted_current)
    return envelope(request, result.__dict__)


@router.get("/settings")
def get_settings(
    request: Request,
    _: Annotated[User, require_roles("admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    values = {item.key: json.loads(item.value_json) for item in db.scalars(select(Setting)).all()}
    return envelope(
        request,
        {
            "snapshot_interval_seconds": values.get("snapshot_interval_seconds", 300),
            "retention_days": values.get("retention_days", 30),
            "secret_status": "configured externally",
        },
    )


@router.get("/controlled/capabilities")
def controlled_capabilities(
    request: Request,
    _: Annotated[User, Depends(current_user)],
) -> dict[str, object]:
    config = get_config()
    controlled = config.controlled_execution
    return envelope(
        request,
        {
            "enabled": config.mode == "CONTROLLED_EXECUTION",
            "mode": config.mode,
            "tools": [
                "safe_log_cleanup",
                "service_restart",
                "config_safe_update",
                "terminate_process",
                "rollback_change",
            ],
            "production_available_tools": (
                ["service_restart", "rollback_change"]
                if _execution_broker_available()
                else []
            ),
            "execution_broker": {
                "available": _execution_broker_available(),
                "scope": "fixed nginx restart only",
            },
            "allowed_services": list(controlled.allowed_services),
            "managed_configs": [
                {"target_id": item.target_id, "validator": item.validator}
                for item in controlled.managed_configs
            ],
            "managed_processes": [
                {"process_name": item.process_name, "service": item.service}
                for item in controlled.managed_processes
            ],
        },
    )


@router.get("/executions")
def list_executions(
    request: Request,
    _: Annotated[User, require_roles("operator", "approver", "admin", "auditor")],
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=200),
) -> dict[str, object]:
    executions = db.scalars(
        select(ExecutionRecord).order_by(ExecutionRecord.created_at.desc()).limit(limit)
    ).all()
    data: list[dict[str, object]] = []
    for item in executions:
        backup = db.scalar(select(BackupRecord).where(BackupRecord.execution_id == item.id))
        verifications = db.scalars(
            select(VerificationResultRecord)
            .where(VerificationResultRecord.execution_id == item.id)
            .order_by(VerificationResultRecord.created_at)
        ).all()
        data.append(
            {
                "change_id": item.id,
                "task_id": item.task_id,
                "tool_name": item.tool_name,
                "target_ref": item.target_ref,
                "status": item.status,
                "created_at": item.created_at,
                "completed_at": item.completed_at,
                "backup_status": backup.status if backup is not None else "STATE_SNAPSHOT",
                "verifications": [
                    {"status": result.status, "details": result.details}
                    for result in verifications
                ],
                "rollback_available": item.status == "SUCCEEDED",
            }
        )
    return envelope(request, data)


@router.put("/settings")
def update_settings(
    body: SettingsUpdate,
    request: Request,
    user: Annotated[User, require_roles("admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    for key, value in body.model_dump().items():
        setting = db.get(Setting, key)
        if setting is None:
            db.add(Setting(key=key, value_json=json.dumps(value)))
        else:
            setting.value_json = json.dumps(value)
            setting.version += 1
    write_audit(db, "SETTINGS_UPDATED", body.model_dump(), actor_id=user.id)
    db.commit()
    return envelope(request, body.model_dump())


def _approval_secret() -> bytes:
    secret = os.getenv("APPROVAL_HMAC_KEY", "").encode()
    if len(secret) < 32:
        raise AppError(
            ErrorCode.INTERNAL_ERROR,
            "approval signing is not configured",
            503,
        )
    return secret


@router.post("/demo/reset", status_code=201)
def reset_demo(
    request: Request,
    user: Annotated[User, require_roles("operator", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if get_config().mode != "DEMO":
        raise AppError(ErrorCode.RBAC_DENIED, "DEMO mode is required", 403)
    candidates = demo_execution_service.reset(_approval_secret())
    write_audit(db, "DEMO_RESET", candidates, actor_id=user.id)
    db.commit()
    return envelope(request, {**candidates, "is_demo": True})


@router.post("/executions/dry-run")
def execution_preview(
    body: ExecutionPreviewRequest,
    request: Request,
    _: Annotated[User, require_roles("operator", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    mode = get_config().mode
    try:
        if mode == "DEMO":
            result = demo_execution_service.require_executor().dry_run(
                body.tool_name, body.arguments
            )
        elif mode == "CONTROLLED_EXECUTION" and body.tool_name == "safe_log_cleanup":
            cleanup_record = _eligible_cleanup_candidate(db, body.arguments)
            result = _production_cleanup_executor().dry_run(
                _cleanup_candidate(cleanup_record),
                use_state=_cleanup_use_state(cleanup_record.path),
            )
        elif mode == "CONTROLLED_EXECUTION" and body.tool_name == "service_restart":
            service = body.arguments.get("service")
            if set(body.arguments) != {"service"} or not isinstance(service, str):
                raise ValueError("ARGUMENT_SCHEMA_INVALID")
            _require_execution_broker()
            result = _production_service_executor().dry_run(service)
        elif mode == "CONTROLLED_EXECUTION" and body.tool_name == "config_safe_update":
            target_id = body.arguments.get("target_id")
            content = body.arguments.get("content")
            if not isinstance(target_id, str) or not isinstance(content, str):
                raise ValueError("ARGUMENT_SCHEMA_INVALID")
            result = _production_config_executor().dry_run(target_id, content)
        elif mode == "CONTROLLED_EXECUTION" and body.tool_name == "terminate_process":
            process_preview_record = _eligible_process_candidate(db, body.arguments)
            result = _production_process_executor().dry_run(
                _process_candidate(process_preview_record)
            )
        else:
            raise AppError(ErrorCode.RBAC_DENIED, "controlled tool is disabled", 403)
    except ValueError as error:
        raise AppError(ErrorCode.VALIDATION_ERROR, "dry-run rejected", 422) from error
    return envelope(request, result)


@router.post("/executions/run")
def execution_run(
    body: ExecutionRunRequest,
    request: Request,
    user: Annotated[User, require_roles("operator", "admin")],
    db: Session = Depends(get_db),
) -> dict[str, object]:
    mode = get_config().mode
    token_hash = hashlib.sha256(body.approval_token.encode()).hexdigest()
    approval = db.scalar(select(Approval).where(Approval.token_hash == token_hash))
    if (
        approval is None
        or approval.status != "APPROVED"
        or approval.requester_id != user.id
        or approval.task_id != body.task_id
        or approval.tool_name != body.tool_name
    ):
        raise AppError(ErrorCode.RBAC_DENIED, "valid approval is required", 403)
    target_ref: str | None = None
    rollback_source: ExecutionRecord | None = None
    attempt_id = str(uuid.uuid4())
    broker_managed = mode == "CONTROLLED_EXECUTION" and body.tool_name == "service_restart"
    if body.tool_name == "rollback_change":
        change_id = body.arguments.get("change_id")
        if isinstance(change_id, str):
            rollback_source = db.get(ExecutionRecord, change_id)
            broker_managed = bool(
                mode == "CONTROLLED_EXECUTION"
                and rollback_source is not None
                and rollback_source.tool_name == "service_restart"
                and (rollback_source.target_ref or "").startswith("systemd:")
            )
    if not broker_managed:
        approval.status = "CONSUMED"
    try:
        if mode == "DEMO":
            result = demo_execution_service.require_executor().execute(
                user_id=user.id,
                task_id=body.task_id,
                tool_name=body.tool_name,
                arguments=body.arguments,
                approval_token=body.approval_token,
                fault=body.fault,
            )
        elif mode == "CONTROLLED_EXECUTION" and body.tool_name == "safe_log_cleanup":
            if body.fault is not None:
                raise ValueError("FAULT_INJECTION_DEMO_ONLY")
            record = _eligible_cleanup_candidate(db, body.arguments)
            target_ref = record.path
            result = _production_cleanup_executor().execute(
                user_id=user.id,
                task_id=body.task_id,
                candidate=_cleanup_candidate(record),
                approval_token=body.approval_token,
                use_state=_cleanup_use_state(record.path),
            )
            record.status = "CONSUMED"
        elif mode == "CONTROLLED_EXECUTION" and body.tool_name == "service_restart":
            if body.fault is not None:
                raise ValueError("FAULT_INJECTION_DEMO_ONLY")
            service = body.arguments.get("service")
            if set(body.arguments) != {"service"} or not isinstance(service, str):
                raise ValueError("ARGUMENT_SCHEMA_INVALID")
            _require_execution_broker()
            target_ref = f"systemd:{service}"
            result = _production_service_executor().execute(
                user_id=user.id,
                task_id=body.task_id,
                service=service,
                approval_token=body.approval_token,
            )
        elif mode == "CONTROLLED_EXECUTION" and body.tool_name == "config_safe_update":
            if body.fault is not None:
                raise ValueError("FAULT_INJECTION_DEMO_ONLY")
            target_id = body.arguments.get("target_id")
            content = body.arguments.get("content")
            if not isinstance(target_id, str) or not isinstance(content, str):
                raise ValueError("ARGUMENT_SCHEMA_INVALID")
            target_ref = f"config:{target_id}"
            result = _production_config_executor().execute(
                user_id=user.id,
                task_id=body.task_id,
                target_id=target_id,
                content=content,
                approval_token=body.approval_token,
            )
        elif mode == "CONTROLLED_EXECUTION" and body.tool_name == "terminate_process":
            if body.fault is not None:
                raise ValueError("FAULT_INJECTION_DEMO_ONLY")
            process_record = _eligible_process_candidate(db, body.arguments)
            target_ref = f"process:{process_record.service}"
            result = _production_process_executor().execute(
                user_id=user.id,
                task_id=body.task_id,
                candidate=_process_candidate(process_record),
                approval_token=body.approval_token,
            )
            process_record.status = "CONSUMED"
        elif mode == "CONTROLLED_EXECUTION" and body.tool_name == "rollback_change":
            if body.fault is not None:
                raise ValueError("FAULT_INJECTION_DEMO_ONLY")
            change_id = body.arguments.get("change_id")
            if not isinstance(change_id, str):
                raise ValueError("ARGUMENT_SCHEMA_INVALID")
            rollback_source = rollback_source or db.get(ExecutionRecord, change_id)
            backup = db.scalar(select(BackupRecord).where(BackupRecord.execution_id == change_id))
            if (
                rollback_source is None
                or rollback_source.task_id != body.task_id
                or rollback_source.status != "SUCCEEDED"
                or rollback_source.target_ref is None
            ):
                raise ValueError("CHANGE_NOT_ROLLBACKABLE")
            if rollback_source.tool_name == "safe_log_cleanup":
                if backup is None:
                    raise ValueError("CHANGE_NOT_ROLLBACKABLE")
                result = _production_cleanup_executor().execute_rollback(
                    user_id=user.id,
                    task_id=body.task_id,
                    change_id=change_id,
                    backup_ref=backup.backup_ref,
                    target_path=rollback_source.target_ref,
                    approval_token=body.approval_token,
                )
            elif rollback_source.tool_name == "config_safe_update" and rollback_source.target_ref.startswith("config:"):
                if backup is None:
                    raise ValueError("CHANGE_NOT_ROLLBACKABLE")
                result = _production_config_executor().execute_rollback(
                    user_id=user.id,
                    task_id=body.task_id,
                    change_id=change_id,
                    target_id=rollback_source.target_ref.removeprefix("config:"),
                    backup_ref=backup.backup_ref,
                    approval_token=body.approval_token,
                )
            elif rollback_source.tool_name == "terminate_process" and rollback_source.target_ref.startswith("process:"):
                result = _production_process_executor().execute_rollback(
                    user_id=user.id,
                    task_id=body.task_id,
                    change_id=change_id,
                    service=rollback_source.target_ref.removeprefix("process:"),
                    approval_token=body.approval_token,
                )
            elif rollback_source.tool_name == "service_restart" and rollback_source.target_ref.startswith("systemd:"):
                _require_execution_broker()
                result = _production_service_executor().execute_rollback(
                    user_id=user.id,
                    task_id=body.task_id,
                    change_id=change_id,
                    service=rollback_source.target_ref.removeprefix("systemd:"),
                    approval_token=body.approval_token,
                )
            else:
                raise ValueError("CHANGE_NOT_ROLLBACKABLE")
            rollback_source.status = "ROLLED_BACK"
        else:
            raise ValueError("CONTROLLED_TOOL_NOT_ENABLED")
    except ValueError as error:
        failure_code = str(error)[:128]
        db.add(
            ExecutionRecord(
                id=attempt_id,
                task_id=body.task_id,
                approval_id=approval.id,
                tool_name=body.tool_name,
                arguments_hash=approval.arguments_hash,
                target_ref=target_ref,
                status="FAILED",
                completed_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            VerificationResultRecord(
                execution_id=attempt_id,
                status="FAILED",
                details=failure_code,
            )
        )
        write_audit(
            db,
            "EXECUTION_REJECTED",
            {
                "approval_id": approval.id,
                "tool_name": body.tool_name,
                "attempt_id": attempt_id,
                "failure_code": failure_code,
            },
            actor_id=user.id,
            task_id=body.task_id,
        )
        db.commit()
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "execution rejected",
            422,
            {"reason_code": failure_code},
        ) from error
    if rollback_source is not None:
        db.add(
            RollbackRecord(
                execution_id=rollback_source.id,
                status="SUCCEEDED",
                details=result.verification,
            )
        )
        db.add(
            VerificationResultRecord(
                execution_id=rollback_source.id,
                status="ROLLBACK_VERIFIED",
                details=result.verification,
            )
        )
        write_audit(
            db,
            "ROLLBACK_COMPLETED",
            {"approval_id": approval.id, "change_id": rollback_source.id},
            actor_id=user.id,
            task_id=body.task_id,
        )
        db.commit()
        return envelope(request, result.__dict__)
    db.add(
        ExecutionRecord(
            id=result.change_id,
            task_id=body.task_id,
            approval_id=approval.id,
            tool_name=body.tool_name,
            arguments_hash=approval.arguments_hash,
            target_ref=target_ref,
            status=result.status,
            completed_at=datetime.now(timezone.utc),
        )
    )
    if result.backup_ref is not None:
        db.add(
            BackupRecord(
                execution_id=result.change_id,
                backup_ref=result.backup_ref,
                status="VERIFIED",
            )
        )
    db.add(
        VerificationResultRecord(
            execution_id=result.change_id,
            status="PASSED" if result.status == "SUCCEEDED" else result.status,
            details=result.verification,
        )
    )
    write_audit(
        db,
        "EXECUTION_COMPLETED",
        {
            "approval_id": approval.id,
            "tool_name": body.tool_name,
            "change_id": result.change_id,
            "status": result.status,
            "verification": result.verification,
        },
        actor_id=user.id,
        task_id=body.task_id,
    )
    db.commit()
    return envelope(request, result.__dict__)


def _eligible_cleanup_candidate(
    db: Session, arguments: dict[str, object]
) -> CleanupCandidateRecord:
    candidate_id = arguments.get("candidate_id")
    if set(arguments) != {"candidate_id"} or not isinstance(candidate_id, str):
        raise ValueError("ARGUMENT_SCHEMA_INVALID")
    record = db.get(CleanupCandidateRecord, candidate_id)
    if record is None or record.status != "ELIGIBLE":
        raise ValueError("CANDIDATE_NOT_FOUND_OR_CONSUMED")
    return record


def _cleanup_candidate(record: CleanupCandidateRecord) -> CleanupCandidate:
    return CleanupCandidate(
        candidate_id=record.id,
        path=record.path,
        size_bytes=record.size_bytes,
        modified_at=_as_utc(record.modified_at),
        inode=record.inode,
        device=record.device,
        snapshot_hash=record.snapshot_hash,
    )


def _eligible_process_candidate(
    db: Session, arguments: dict[str, object]
) -> ProcessCandidateRecord:
    candidate_id = arguments.get("candidate_id")
    if set(arguments) != {"candidate_id"} or not isinstance(candidate_id, str):
        raise ValueError("ARGUMENT_SCHEMA_INVALID")
    record = db.get(ProcessCandidateRecord, candidate_id)
    if record is None or record.status != "ELIGIBLE":
        raise ValueError("PROCESS_CANDIDATE_NOT_FOUND_OR_CONSUMED")
    return record


def _process_candidate(record: ProcessCandidateRecord) -> ProcessCandidate:
    return ProcessCandidate(
        candidate_id=record.id,
        pid=record.pid,
        name=record.process_name,
        start_ticks=record.start_ticks,
        service=record.service,
    )


def _cleanup_use_state(path: str) -> FileUseState:
    result = KylinGuardMCPClient().call_tool("open_file_lookup", {"path": path})
    if result.status != "SUCCEEDED" or result.data.get("supported") is not True:
        return FileUseState.UNKNOWN
    return FileUseState.OPEN if str(result.data.get("raw", "")).strip() else FileUseState.NOT_OPEN


def _production_cleanup_executor() -> ControlledCleanupExecutor:
    config = get_config().controlled_execution
    app_config = get_config()
    policy = CleanupPolicy(
        allowed_roots=app_config.controlled_cleanup_roots(),
        protected_paths=config.protected_paths,
        minimum_age_days=config.minimum_age_days,
        minimum_size_bytes=config.minimum_size_bytes,
    )
    return ControlledCleanupExecutor(
        policy=policy,
        backup_root=config.backup_root,
        approvals=ApprovalTokenManager(_approval_secret()),
    )


def _production_service_executor() -> ControlledServiceExecutor:
    config = get_config().controlled_execution
    broker = LocalExecutionBroker(config.executor_socket_path)
    return ControlledServiceExecutor(
        executable=config.systemctl_path,
        allowed_services=config.allowed_services,
        approvals=ApprovalTokenManager(_approval_secret()),
        runner=BrokerSystemctlRunner(config.systemctl_path, broker),
    )


def _execution_broker_available() -> bool:
    return LocalExecutionBroker(get_config().controlled_execution.executor_socket_path).is_available()


def _require_execution_broker() -> None:
    if not _execution_broker_available():
        raise ValueError("EXECUTION_BROKER_UNAVAILABLE")


def _production_config_executor() -> ControlledConfigExecutor:
    config = get_config().controlled_execution
    targets = tuple(
        ConfigTarget(
            target_id=item.target_id,
            path=item.path,
            validator=item.validator,
            validator_path=item.validator_path,
        )
        for item in config.managed_configs
    )
    return ControlledConfigExecutor(
        targets=targets,
        backup_root=config.backup_root,
        approvals=ApprovalTokenManager(_approval_secret()),
    )


def _production_process_executor() -> ControlledProcessExecutor:
    config = get_config().controlled_execution
    managed = {item.process_name: item.service for item in config.managed_processes}
    service_executor = _production_service_executor()
    return ControlledProcessExecutor(
        managed_processes=managed,
        approvals=ApprovalTokenManager(_approval_secret()),
        restorer=service_executor,
    )
