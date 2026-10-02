"""Learning use cases: explicit authorization, atomic replay, optimistic writes."""

import hashlib
import json
from dataclasses import asdict
from uuid import uuid4
from zoneinfo import ZoneInfo

from .catalog import get_method
from .domain import LearningSession, PolicyError, utc_now
from .ports import ModelPort, UnitOfWork
from .timing_domain import clean_note, segment_anomalies, span_seconds


def serialize(value: LearningSession) -> dict:
    result = asdict(value)
    result.pop("owner_id")
    result.pop("time_segments")
    for field in ("started_at", "ended_at"):
        result[field] = result[field].isoformat() if result[field] else None
    now = utc_now()
    segments = []
    review_required = False
    for segment in value.time_segments:
        anomalies = segment_anomalies(
            started_at=segment.started_at,
            ended_at=segment.ended_at,
            day_timezone=value.day_timezone,
            now=now,
        )
        excluded = segment.excluded_at is not None
        needs_review = bool(anomalies) and not excluded
        review_required = review_required or needs_review
        segments.append(
            {
                "id": segment.id,
                "started_at": segment.started_at.isoformat(),
                "ended_at": segment.ended_at.isoformat() if segment.ended_at else None,
                # Counted duration: an excluded span contributes nothing.
                "duration_seconds": 0
                if excluded
                else span_seconds(segment.started_at, segment.ended_at, now),
                "excluded": excluded,
                "excluded_at": segment.excluded_at.isoformat() if segment.excluded_at else None,
                "original_ended_at": (
                    segment.original_ended_at.isoformat() if segment.original_ended_at else None
                ),
                "correction_note": segment.correction_note,
                "anomalies": anomalies,
                "review_required": needs_review,
            }
        )
    result["effective_duration_seconds"] = value.effective_duration_seconds
    result["time_segments"] = segments
    # Overnight or implausibly long spans are surfaced, never silently counted.
    result["timing_review_required"] = review_required
    return result


class LearningService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(
        self,
        owner: str,
        timezone_name: str,
        action: str,
        body: dict,
        key: str,
        session_id: str | None = None,
        version: int | None = None,
    ) -> dict:
        if not key or len(key) > 128 or key != body["operation_id"]:
            raise PolicyError("VALIDATION_ERROR", "Idempotency-Key must equal operation_id.", 422)
        fingerprint = hashlib.sha256(
            json.dumps({"body": body, "version": version}, sort_keys=True).encode()
        ).hexdigest()
        operation = f"session:{action}:{session_id or ''}"
        self.uow.lock_owner(owner)
        replay = self.uow.replay(owner, operation, key, fingerprint)
        if replay is not None:
            return replay
        if action == "create":
            if self.uow.sessions.current(owner):
                raise PolicyError("ACTIVE_SESSION_EXISTS", "Continue or end the current session.")
            subject = body.get("subject_id")
            knowledge_point_id = body.get("knowledge_point_id")
            if knowledge_point_id:
                point = self.uow.knowledge.get_active_point(owner, knowledge_point_id)
                if subject and subject != point["subject_id"]:
                    raise PolicyError(
                        "VALIDATION_ERROR", "Knowledge point must match the session subject.", 422
                    )
                subject = point["subject_id"]
            if subject and not self.uow.owns_subject(owner, subject):
                raise PolicyError("RESOURCE_NOT_FOUND", "Resource not found.", 404)
            previous_session_id = body.get("previous_session_id")
            if previous_session_id:
                previous = self.uow.sessions.get(owner, previous_session_id)
                if previous.status != "ended":
                    raise PolicyError(
                        "VALIDATION_ERROR", "Only an ended session can be continued.", 422
                    )
            method_id = body.get("method_id")
            if method_id and get_method(method_id) is None:
                raise PolicyError("VALIDATION_ERROR", "Learning method is unavailable.", 422)
            now = utc_now()
            value = LearningSession(
                str(uuid4()),
                owner,
                body.get("goal"),
                subject,
                "active",
                1,
                now,
                None,
                timezone_name,
                now.astimezone(ZoneInfo(timezone_name)).date().isoformat(),
                body.get("timing_enabled", False),
                method_id,
                body.get("kind", "free"),
                previous_session_id,
                body.get("resume_note"),
                knowledge_point_id,
            )
            value = self.uow.sessions.add(value)
        else:
            value = self.uow.sessions.get(owner, session_id or "")
            if version is None:
                raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
            value = self.uow.sessions.transition(value, action, version)
        response = serialize(value)
        self.uow.remember(owner, operation, key, fingerprint, response)
        self.uow.commit()
        return response

    def correct_segment(self, owner, session_id, segment_id, body, key, version):
        """Correct one timer span so it matches reality.

        Corrections may only shorten a span or exclude it: the timer can be
        brought down to what actually happened, never inflated, and the session
        is never rewritten to claim more study than the learner reports.
        """
        from .schemas import CorrectTimeSegmentInput

        data = CorrectTimeSegmentInput.model_validate(body).model_dump(exclude_unset=True)
        operation_id = str(data.get("operation_id", ""))
        if not operation_id or len(operation_id) > 128 or operation_id != key:
            raise PolicyError("VALIDATION_ERROR", "Idempotency-Key must equal operation_id.", 422)
        if version is None:
            raise PolicyError("PRECONDITION_REQUIRED", "If-Match is required.", 428)
        changes = {}
        if "ended_at" in data:
            changes["ended_at"] = data["ended_at"]
        if "exclude" in data:
            changes["exclude"] = data["exclude"]
        if "correction_note" in data:
            changes["correction_note"] = clean_note(data["correction_note"])
        fingerprint = hashlib.sha256(
            json.dumps(
                {"body": body, "version": version, "segment": segment_id}, sort_keys=True
            ).encode()
        ).hexdigest()
        operation = f"session:segment:{session_id}:{segment_id}"
        self.uow.lock_owner(owner)
        replay = self.uow.replay(owner, operation, key, fingerprint)
        if replay is not None:
            return replay
        value = self.uow.sessions.get(owner, session_id)
        if value.version != version:
            error = PolicyError("VERSION_CONFLICT", "Session changed; reload before editing.", 409)
            error.current_version = value.version
            raise error
        value = self.uow.sessions.correct_segment(value, segment_id, changes, version)
        response = serialize(value)
        self.uow.remember(owner, operation, key, fingerprint, response)
        self.uow.commit()
        return response


class AdvisorService:
    def __init__(self, model: ModelPort):
        self.model = model

    def advise(self, evidence: list[dict], budget: int = 4096) -> dict:
        # This initial adapter budgets serialized input characters, not provider tokens.
        if not isinstance(evidence, list) or any(
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not isinstance(item.get("version"), int)
            or not isinstance(item.get("text"), str)
            for item in evidence
        ):
            raise PolicyError("VALIDATION_ERROR", "Evidence needs id, version and text.", 422)
        if len({item["id"] for item in evidence}) != len(evidence):
            raise PolicyError("VALIDATION_ERROR", "Evidence ids must be unique.", 422)
        if budget < 1 or budget > 4096 or len(json.dumps(evidence)) > budget:
            raise PolicyError("QUOTA_EXCEEDED", "Evidence exceeds the analysis budget.", 429)
        output = self.model.advise(evidence, budget)
        allowed = {item["id"]: item for item in evidence}
        if not isinstance(output, dict) or set(output) != {
            "facts",
            "inferences",
            "missing_information",
        }:
            raise PolicyError("INVALID_MODEL_OUTPUT", "Model output is invalid.", 502)
        if any(not isinstance(output[field], list) for field in output):
            raise PolicyError("INVALID_MODEL_OUTPUT", "Model output lists are invalid.", 502)
        if any(not isinstance(item, str) for item in output["missing_information"]):
            raise PolicyError("INVALID_MODEL_OUTPUT", "Model output text is invalid.", 502)
        for inference in output["inferences"]:
            if (
                not isinstance(inference, dict)
                or not isinstance(inference.get("text"), str)
                or not isinstance(inference.get("source_refs"), list)
                or not inference["source_refs"]
            ):
                raise PolicyError(
                    "INVALID_MODEL_OUTPUT", "Inference needs evidence references.", 502
                )
            for ref in inference["source_refs"]:
                if not isinstance(ref, dict) or not isinstance(ref.get("id"), str):
                    raise PolicyError(
                        "INVALID_MODEL_OUTPUT", "Inference reference is invalid.", 502
                    )
                source = allowed.get(ref["id"])
                if source is None or source["version"] != ref.get("version"):
                    raise PolicyError(
                        "INVALID_MODEL_OUTPUT", "Inference referenced unknown evidence.", 502
                    )
        for fact in output["facts"]:
            if not isinstance(fact, dict) or not isinstance(fact.get("source_id"), str):
                raise PolicyError("INVALID_MODEL_OUTPUT", "Model fact is invalid.", 502)
            source = allowed.get(fact.get("source_id"))
            if source is None or fact.get("source_version") != source.get("version"):
                raise PolicyError("INVALID_MODEL_OUTPUT", "Model referenced unknown evidence.", 502)
            if fact.get("text") != source.get("text"):
                raise PolicyError(
                    "INVALID_MODEL_OUTPUT", "Fact differs from supplied evidence.", 502
                )
        return output
