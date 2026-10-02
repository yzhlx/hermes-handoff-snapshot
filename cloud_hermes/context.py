"""Cloud Hermes Core — context builder (Track A owns).

OWNER: Track A (Gateway/Runtime). Resolves role/profile and performs REAL Memory Retrieval
before the provider call. Retrieved memory actually influences the system prompt.
"""
from __future__ import annotations

from .memory import MemoryStore, normalize_role_namespace

HERMES_SYSTEM_INSTRUCTIONS = (
    "You are Hermes, a learning assistant. Use simplified Chinese when possible. "
    "Give actionable next steps, distinguish facts from inference, ask for missing "
    "evidence, do not claim that viewing an answer means mastery, and do not provide "
    "medical diagnoses or invent learning records."
)


class ContextBuilder:
    def __init__(self, memory: MemoryStore):
        self.memory = memory

    def build(self, role_id: str, user_message: str, memory_limit: int = 10) -> dict:
        memories = self.memory.retrieve(role_id, limit=memory_limit)
        memory_text = "\n".join(f"- ({m['namespace']}) {m['content']}" for m in memories)
        system = HERMES_SYSTEM_INSTRUCTIONS
        if memory_text:
            system += "\n\n# 已批准的长期记忆（ retrieval 真实结果，仅作参考，不得声称已自动记忆）\n" + memory_text
        # The profile/role is resolved; V1 wires only `master`, others fall back to master.
        resolved_role = role_id if role_id in _KNOWN_ROLES else "master"
        return {
            "system": system,
            "role_id": resolved_role,
            "memory": memories,
            "memory_count": len(memories),
        }


_KNOWN_ROLES = {
    "master", "signal_teacher", "graduate_senior", "supportive_senior", "ruthless_humiliator",
}
