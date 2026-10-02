"""Deterministic provider adapter, with an explicit capability manifest."""

from typing import ClassVar


class MockModel:
    capabilities: ClassVar[dict] = {
        "text": True,
        "image": False,
        "pdf": False,
        "tool_calls": False,
        "structured_output": True,
        "max_budget": 4096,
    }

    def advise(self, evidence, budget):
        return {
            "facts": [
                {"text": item["text"], "source_id": item["id"], "source_version": item["version"]}
                for item in evidence
            ],
            "inferences": [],
            "missing_information": [] if evidence else ["Provide a learning record."],
        }
