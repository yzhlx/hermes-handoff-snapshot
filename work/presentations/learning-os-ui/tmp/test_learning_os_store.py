import base64
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = ROOT / "outputs" / "learning-os-store.py"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def load_module():
    spec = importlib.util.spec_from_file_location("learning_os_store", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EventStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store_module = load_module()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.db_path = self.root / "learning-os.db"
        self.store = self.store_module.EventStore(self.db_path)

    def tearDown(self):
        self.store.close()
        self.temporary.cleanup()

    def test_append_and_replay_survive_reopen(self):
        first = self.store.append(
            "EvidenceExtracted",
            "knowledge-point",
            "laplace-roc",
            {"submission_id": "submission-1", "evidence_id": "evidence-1"},
        )
        second = self.store.append(
            "AssessmentRequested",
            "knowledge-point",
            "laplace-roc",
            {"evidence_id": "evidence-1", "job_id": "job-1"},
        )
        self.store.close()
        self.store = self.store_module.EventStore(self.db_path)
        events = self.store.replay("knowledge-point", "laplace-roc")
        self.assertEqual([event["event_id"] for event in events], [first["event_id"], second["event_id"]])
        self.assertLess(events[0]["sequence"], events[1]["sequence"])

    def test_sql_update_and_delete_are_rejected(self):
        event = self.store.append(
            "EvidenceExtracted",
            "knowledge-point",
            "laplace-roc",
            {"submission_id": "submission-1", "evidence_id": "evidence-1"},
        )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
            self.store.connection.execute(
                "UPDATE events SET event_type = ? WHERE event_id = ?",
                ("Changed", event["event_id"]),
            )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
            self.store.connection.execute(
                "DELETE FROM events WHERE event_id = ?",
                (event["event_id"],),
            )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
            self.store.connection.execute(
                """
                INSERT OR REPLACE INTO events (
                  event_id, event_type, aggregate_type, aggregate_id,
                  occurred_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event["event_id"],
                    event["event_type"],
                    event["aggregate_type"],
                    event["aggregate_id"],
                    event["occurred_at"],
                    '{"replaced":true}',
                ),
            )

    def test_submission_lookup_returns_original_evidence(self):
        expected = self.store.append(
            "EvidenceExtracted",
            "knowledge-point",
            "laplace-roc",
            {"submission_id": "same-id", "evidence_id": "evidence-1"},
        )
        found = self.store.find_evidence_by_submission_id("same-id")
        self.assertEqual(found["event_id"], expected["event_id"])
        self.assertIsNone(self.store.find_evidence_by_submission_id("missing"))

    def test_projection_records_assessment_and_f_state(self):
        self.store.append(
            "EvidenceExtracted",
            "knowledge-point",
            "laplace-roc",
            {"submission_id": "s", "evidence_id": "e1"},
        )
        self.store.append(
            "AssessmentRecorded",
            "knowledge-point",
            "laplace-roc",
            {
                "assessment_id": "a1",
                "evidence_id": "e1",
                "f_state": "F3",
                "summary": "核心结论正确",
            },
        )
        state = self.store_module.project_events(
            self.store.replay("knowledge-point", "laplace-roc")
        )
        self.assertEqual(state["f_state"], "F3")
        self.assertEqual(state["evidence_ids"], ["e1"])
        self.assertEqual(state["latest_assessment"]["assessment_id"], "a1")
        self.assertEqual(state["assessment_status"], "recorded")

    def test_projection_rejects_mixed_aggregates(self):
        events = [
            {"aggregate_type": "knowledge-point", "aggregate_id": "a", "event_type": "EvidenceExtracted", "payload": {"evidence_id": "e1"}},
            {"aggregate_type": "knowledge-point", "aggregate_id": "b", "event_type": "EvidenceExtracted", "payload": {"evidence_id": "e2"}},
        ]
        with self.assertRaises(self.store_module.AggregateIdentityError):
            self.store_module.project_events(events)


class ArtifactRepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store_module = load_module()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = self.store_module.ArtifactRepository(self.root / "artifacts")

    def tearDown(self):
        self.temporary.cleanup()

    def test_writes_and_verifies_immutable_evidence(self):
        manifest = self.repository.write_evidence(
            "evidence-1",
            {"schemaVersion": 2, "pages": []},
            [{"filename": "page-001.png", "bytes": PNG}],
            "ROC 为收敛域",
        )
        self.assertEqual(manifest["evidence_id"], "evidence-1")
        self.assertTrue(self.repository.verify_manifest(manifest))
        target = self.root / "artifacts" / "evidence-1"
        self.assertEqual(json.loads((target / "handwriting.json").read_text(encoding="utf-8"))["schemaVersion"], 2)
        self.assertEqual((target / "page-001.png").read_bytes(), PNG)
        with self.assertRaises(FileExistsError):
            self.repository.write_evidence(
                "evidence-1",
                {"schemaVersion": 2, "pages": []},
                [{"filename": "page-001.png", "bytes": PNG}],
                "duplicate",
            )

    def test_hash_mismatch_is_detected(self):
        manifest = self.repository.write_evidence(
            "evidence-2",
            {"schemaVersion": 2, "pages": []},
            [{"filename": "page-001.png", "bytes": PNG}],
            "text",
        )
        target = self.root / "artifacts" / "evidence-2" / "page-001.png"
        target.write_bytes(b"changed")
        self.assertFalse(self.repository.verify_manifest(manifest))

    def test_rejects_unsafe_artifact_names(self):
        with self.assertRaisesRegex(ValueError, "filename"):
            self.repository.write_evidence(
                "evidence-3",
                {"schemaVersion": 2, "pages": []},
                [{"filename": "../outside.png", "bytes": PNG}],
                "text",
            )


if __name__ == "__main__":
    unittest.main()
