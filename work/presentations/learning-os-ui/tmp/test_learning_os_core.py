import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = ROOT / "outputs" / "learning-os-core.py"


def load_module():
    spec = importlib.util.spec_from_file_location("learning_os_core", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LearningOSCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core_module = load_module()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.core = self.core_module.LearningOSCore(Path(self.temporary.name))

    def tearDown(self):
        self.core.close()
        self.temporary.cleanup()

    def test_today_prefers_active_then_high_priority_due_task(self):
        self.core.create_task(
            {"title": "低优先任务", "study_date": "2026-07-21", "priority": "low"}
        )
        high = self.core.create_task(
            {"title": "高优先任务", "study_date": "2026-07-21", "priority": "high"}
        )
        active = self.core.create_task(
            {"title": "进行中任务", "study_date": "2026-07-21", "priority": "low"}
        )
        self.core.transition_task(active["id"], "active")
        dashboard = self.core.today("2026-07-21", "09:00")
        self.assertEqual(dashboard["current_task"]["id"], active["id"])
        self.core.transition_task(active["id"], "completed")
        dashboard = self.core.today("2026-07-21", "09:00")
        self.assertEqual(dashboard["current_task"]["id"], high["id"])

    def test_daily_review_selects_five_due_high_priority_unmastered_questions(self):
        for index, priority in enumerate(("high", "high", "medium", "low", "low", "low")):
            question = self.core.create_error_question(
                {
                    "subject": "高等数学",
                    "title": f"错题 {index}",
                    "priority": priority,
                    "mastery": "not_mastered",
                    "next_review_date": "2026-07-20",
                }
            )
            if index == 5:
                self.core.update_error_question(question["id"], {"mastery": "mastered"})
        items = self.core.daily_review("2026-07-21")
        self.assertEqual(len(items), 5)
        self.assertEqual([item["priority"] for item in items[:2]], ["high", "high"])

    def test_review_outcome_adjusts_next_review_and_history(self):
        question = self.core.create_error_question(
            {"subject": "高等数学", "title": "极限错题", "priority": "high"}
        )
        review = self.core.record_review(question["id"], "2026-07-21", "partial")
        detail = self.core.get_error_question(question["id"])
        self.assertEqual(review["outcome"], "partial")
        self.assertEqual(detail["next_review_date"], "2026-07-25")
        self.assertEqual(detail["review_count"], 1)

    def test_high_pressure_low_energy_advice_is_non_medical(self):
        record = self.core.record_status(
            {
                "recorded_on": "2026-07-21",
                "mood": 2,
                "energy": 1,
                "stress": 5,
                "fatigued": True,
                "willing_to_continue": False,
            }
        )
        self.assertEqual(record["advice"]["level"], "long_rest")
        self.assertNotIn("诊断", record["advice"]["message"])

    def test_chat_message_keeps_optional_error_question_link(self):
        question = self.core.create_error_question(
            {"subject": "高等数学", "title": "导数错题", "priority": "medium"}
        )
        chat = self.core.create_chat({"title": "导数讨论"})
        message = self.core.add_chat_message(
            chat["id"],
            {"role": "user", "content": "这里为什么错？", "link_type": "error_question", "link_id": question["id"]},
        )
        self.assertEqual(message["link_type"], "error_question")
        self.assertEqual(message["link_id"], question["id"])

    def test_ai_settings_persist_provider_metadata_without_a_secret(self):
        saved = self.core.update_ai_settings(
            {
                "base_url": "https://example.test/v1/chat/completions",
                "protocol": "chat_completions",
                "model": "gemini-2.5-flash",
                "timeout_seconds": 17,
            }
        )
        self.assertEqual(saved["protocol"], "chat_completions")
        self.assertEqual(saved["timeout_seconds"], 17)
        self.assertNotIn("api_key", saved)
        self.assertEqual(self.core.get_ai_settings()["model"], "gemini-2.5-flash")
        with self.assertRaisesRegex(ValueError, "must not be stored"):
            self.core.update_ai_settings({"api_key": "QA_TEST_SECRET_DO_NOT_STORE"})
        database_bytes = (Path(self.temporary.name) / "learning-os-v2.db").read_bytes()
        self.assertNotIn(b"QA_TEST_SECRET_DO_NOT_STORE", database_bytes)


if __name__ == "__main__":
    unittest.main()
