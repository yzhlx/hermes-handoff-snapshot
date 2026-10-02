"""Use cases for the optional AI advisor.

Facts are assembled deterministically from the owner's own records, so the
surface stays useful when the model is unavailable. Model inferences are
validated against the evidence bundle before they are shown; a violation
degrades the run instead of publishing unsafe text.

The provider call happens *outside* the owner lock so a slow or failing model
never holds a database transaction open.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from .advisor_domain import (
    DEGRADATION_MODEL_ERROR,
    DEGRADATION_MODEL_UNAVAILABLE,
    POLICY_VERSION,
    RULE_VERSION,
    AdvisorPolicyError,
    build_facts,
    build_missing,
    data_version,
    summarize,
    validate_inferences,
    validate_missing,
)
from .advisor_ports import AdvisorModelUnavailable
from .advisor_schemas import CancelAdvisorInput, CreateAdvisorInput
from .domain import PolicyError


class AdvisorService:
    def __init__(self, uow, model):
        self.uow = uow
        self.model = model

    @staticmethod
    def _op(data, key):
        operation_id = str(data.get("operation_id", ""))
        if not operation_id or len(operation_id) > 128 or operation_id != key:
            raise PolicyError("VALIDATION_ERROR", "Idempotency-Key must equal operation_id.", 422)
        fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        return operation_id, fingerprint

    def _write(self, owner, operation, key, fingerprint, callback):
        self.uow.lock_owner(owner)
        cached = self.uow.replay(owner, operation, key, fingerprint)
        if cached is not None:
            return cached
        result = callback()
        result = json.loads(json.dumps(result, default=lambda value: value.isoformat()))
        self.uow.remember(owner, operation, key, fingerprint, result)
        self.uow.commit()
        return result

    @staticmethod
    def _evidence_refs(evidence):
        return [
            {
                "id": record["id"],
                "kind": "attempt",
                "version": record["version"],
                "label": record["problem_title"],
            }
            for record in evidence["records"]
        ]

    def _evaluate(self, evidence, allowed, topic, missing):
        """Ask the provider and validate what comes back.

        Any provider fault degrades the run; it never becomes a 500 and it never
        publishes unvalidated text.
        """

        if not evidence["records"]:
            # No records: stay honest and skip the model entirely.
            return [], "insufficient", None
        try:
            raw = self.model.analyze({"topic": topic}, evidence) or {}
            inferences = validate_inferences(raw.get("inferences", []), allowed)
            for item in validate_missing(raw.get("missing_information", []), allowed):
                if item not in missing:
                    missing.append(item)
            return inferences, "ready", None
        except AdvisorModelUnavailable:
            return [], "degraded", DEGRADATION_MODEL_UNAVAILABLE
        except AdvisorPolicyError as exc:
            return [], "blocked", exc.reason
        except Exception:  # noqa: BLE001 - an unexpected provider fault must degrade, not 500
            return [], "degraded", DEGRADATION_MODEL_ERROR

    def analyze(self, owner, body, key):
        data = CreateAdvisorInput.model_validate(body).model_dump(mode="json")
        op, fp = self._op(data, key)

        # Fast path: a replay must not trigger a second provider call.
        cached = self.uow.replay(owner, "advisor:analyze", op, fp)
        if cached is not None:
            return cached

        evidence = self.uow.advisor.collect_evidence(
            owner, data.get("subject_id"), data.get("knowledge_point_id")
        )
        facts = build_facts(evidence)
        missing = build_missing(evidence)
        allowed = {record["id"]: record["version"] for record in evidence["records"]}
        inferences, status, reason = self._evaluate(evidence, allowed, data.get("topic"), missing)

        def run():
            return self.uow.advisor.create_run(
                owner,
                {
                    "request_id": op,
                    "topic": data.get("topic"),
                    "subject_id": data.get("subject_id"),
                    "knowledge_point_id": data.get("knowledge_point_id"),
                    "status": status,
                    "degradation_reason": reason,
                    "facts": facts,
                    "inferences": inferences,
                    "missing_information": missing,
                    "summary": summarize(facts, inferences, missing),
                    "evidence_count": len(evidence["records"]),
                    "evidence_refs": self._evidence_refs(evidence),
                    "data_version": data_version(evidence),
                    "model_id": self.model.model_id,
                    "provider": getattr(self.model, "provider", self.model.model_id),
                    "prompt_version": self.model.prompt_version,
                    "policy_version": POLICY_VERSION,
                    "rule_version": RULE_VERSION,
                    "externally_hosted": self.model.externally_hosted,
                },
            )

        return self._write(owner, "advisor:analyze", op, fp, run)

    def get(self, owner, run_id):
        self.uow.lock_owner(owner)
        value = self.uow.advisor.get_run(owner, run_id)
        self.uow.commit()
        return value

    def list(self, owner, *, limit=50, cursor=None):
        if not 1 <= limit <= 100:
            raise PolicyError("VALIDATION_ERROR", "Limit must be between 1 and 100.", 422)
        self.uow.lock_owner(owner)
        rows = self.uow.advisor.list_runs(owner, limit + 1, cursor)
        self.uow.commit()
        items = rows[:limit]
        next_cursor = None
        if len(rows) > limit and items:
            last = items[-1]
            # URL-safe opaque cursor: naive UTC timestamp + id (no '+' offset).
            created = datetime.fromisoformat(last["created_at"]).replace(tzinfo=None)
            next_cursor = f"{created.isoformat()}|{last['id']}"
        return {"items": items, "next_cursor": next_cursor}

    def cancel(self, owner, run_id, body, key):
        data = CancelAdvisorInput.model_validate(body).model_dump(mode="json")
        op, fp = self._op(data, key)
        return self._write(
            owner,
            f"advisor:cancel:{run_id}",
            op,
            fp,
            lambda: self.uow.advisor.cancel_run(owner, run_id),
        )
