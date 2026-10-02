from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import threading
from urllib.parse import urlparse
import uuid


PRIORITIES = ("high", "medium", "low")
TASK_STATUSES = ("planned", "active", "paused", "completed", "skipped", "postponed")
MASTERY_STATES = ("not_mastered", "partial", "mastered")
REVIEW_OUTCOMES = ("mastered", "partial", "cannot", "careless", "skipped")
AI_PROTOCOLS = ("responses", "chat_completions")
DEFAULT_AI_TIMEOUT_SECONDS = 30
MIN_AI_TIMEOUT_SECONDS = 5
MAX_AI_TIMEOUT_SECONDS = 120


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _id() -> str:
    return str(uuid.uuid4())


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _parse_json(value: str | None, fallback):
    return json.loads(value) if value else fallback


class LearningOSCore:
    """Local-first domain store. Credentials and binary assets live outside this database."""

    def __init__(self, data_root: str | Path):
        self.data_root = Path(data_root)
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(
            self.data_root / "learning-os-v2.db", check_same_thread=False
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.lock = threading.RLock()
        self._create_schema()

    def _create_schema(self):
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS subjects (
              id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
              enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY, title TEXT NOT NULL, subject_id TEXT,
              study_date TEXT NOT NULL, start_time TEXT, estimated_minutes INTEGER,
              due_at TEXT, priority TEXT NOT NULL, status TEXT NOT NULL,
              needs_review INTEGER NOT NULL DEFAULT 0, notes TEXT,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              FOREIGN KEY(subject_id) REFERENCES subjects(id)
            );
            CREATE INDEX IF NOT EXISTS tasks_by_date ON tasks(study_date, status, priority);
            CREATE TABLE IF NOT EXISTS error_questions (
              id TEXT PRIMARY KEY, subject TEXT NOT NULL, chapter TEXT, title TEXT,
              problem_text TEXT, work_text TEXT, reasoning_text TEXT, correct_answer TEXT,
              explanation TEXT, notes TEXT, tags_json TEXT NOT NULL, error_types_json TEXT NOT NULL,
              difficulty TEXT, priority TEXT NOT NULL, mastery TEXT NOT NULL,
              next_review_date TEXT, review_count INTEGER NOT NULL DEFAULT 0,
              last_failed_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS error_questions_review
              ON error_questions(subject, next_review_date, priority, mastery);
            CREATE TABLE IF NOT EXISTS review_records (
              id TEXT PRIMARY KEY, error_question_id TEXT NOT NULL, reviewed_on TEXT NOT NULL,
              outcome TEXT NOT NULL, notes TEXT, next_review_date TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(error_question_id) REFERENCES error_questions(id)
            );
            CREATE TABLE IF NOT EXISTS error_analyses (
              id TEXT PRIMARY KEY, error_question_id TEXT NOT NULL, result_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(error_question_id) REFERENCES error_questions(id)
            );
            CREATE INDEX IF NOT EXISTS analyses_by_question ON error_analyses(error_question_id, created_at);
            CREATE TABLE IF NOT EXISTS status_records (
              id TEXT PRIMARY KEY, recorded_on TEXT NOT NULL, mood INTEGER, energy INTEGER,
              stress INTEGER, fatigued INTEGER NOT NULL, willing_to_continue INTEGER,
              notes TEXT, advice_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS status_by_day ON status_records(recorded_on, created_at);
            CREATE TABLE IF NOT EXISTS chats (
              id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
              id TEXT PRIMARY KEY, chat_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL,
              link_type TEXT, link_id TEXT, created_at TEXT NOT NULL,
              FOREIGN KEY(chat_id) REFERENCES chats(id)
            );
            CREATE INDEX IF NOT EXISTS messages_by_chat ON chat_messages(chat_id, created_at);
            CREATE TABLE IF NOT EXISTS ai_settings (
              id INTEGER PRIMARY KEY CHECK (id = 1), base_url TEXT NOT NULL,
              protocol TEXT NOT NULL, model TEXT NOT NULL,
              timeout_seconds INTEGER NOT NULL DEFAULT 30, updated_at TEXT NOT NULL
            );
            """
        )
        columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(ai_settings)")}
        if "timeout_seconds" not in columns:
            self.connection.execute(
                "ALTER TABLE ai_settings ADD COLUMN timeout_seconds INTEGER NOT NULL DEFAULT 30"
            )
        self.connection.commit()

    def _one(self, query: str, parameters=()):
        row = self.connection.execute(query, parameters).fetchone()
        return dict(row) if row else None

    def _many(self, query: str, parameters=()):
        return [dict(row) for row in self.connection.execute(query, parameters).fetchall()]

    @staticmethod
    def _require_choice(value: object, choices: tuple[str, ...], label: str) -> str:
        if value not in choices:
            raise ValueError(f"{label} is invalid")
        return str(value)

    def create_subject(self, name: str, enabled: bool = True) -> dict:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Subject name is required")
        record = {"id": _id(), "name": name.strip(), "enabled": int(bool(enabled)), "created_at": _now()}
        with self.lock:
            self.connection.execute(
                "INSERT INTO subjects(id,name,enabled,created_at) VALUES(:id,:name,:enabled,:created_at)", record
            )
            self.connection.commit()
        return {**record, "enabled": bool(record["enabled"])}

    def create_task(self, payload: dict) -> dict:
        if not isinstance(payload, dict) or not isinstance(payload.get("title"), str) or not payload["title"].strip():
            raise ValueError("Task title is required")
        if not isinstance(payload.get("study_date"), str) or not payload["study_date"]:
            raise ValueError("Task study_date is required")
        priority = self._require_choice(payload.get("priority", "medium"), PRIORITIES, "Task priority")
        now = _now()
        record = {
            "id": _id(), "title": payload["title"].strip(), "subject_id": payload.get("subject_id"),
            "study_date": payload["study_date"], "start_time": payload.get("start_time"),
            "estimated_minutes": payload.get("estimated_minutes"), "due_at": payload.get("due_at"),
            "priority": priority, "status": "planned", "needs_review": int(bool(payload.get("needs_review"))),
            "notes": payload.get("notes"), "created_at": now, "updated_at": now,
        }
        with self.lock:
            self.connection.execute(
                """INSERT INTO tasks VALUES(:id,:title,:subject_id,:study_date,:start_time,:estimated_minutes,
                :due_at,:priority,:status,:needs_review,:notes,:created_at,:updated_at)""", record
            )
            self.connection.commit()
        return self.get_task(record["id"])

    def get_task(self, task_id: str) -> dict:
        record = self._one("SELECT * FROM tasks WHERE id=?", (task_id,))
        if record is None:
            raise KeyError(task_id)
        record["needs_review"] = bool(record["needs_review"])
        return record

    def list_tasks(self, study_date: str | None = None) -> list[dict]:
        if study_date:
            rows = self._many("SELECT * FROM tasks WHERE study_date=? ORDER BY start_time, created_at", (study_date,))
        else:
            rows = self._many("SELECT * FROM tasks ORDER BY study_date, start_time, created_at")
        for row in rows:
            row["needs_review"] = bool(row["needs_review"])
        return rows

    def update_task(self, task_id: str, changes: dict) -> dict:
        current = self.get_task(task_id)
        allowed = {"title", "subject_id", "study_date", "start_time", "estimated_minutes", "due_at", "priority", "needs_review", "notes"}
        values = {key: value for key, value in changes.items() if key in allowed}
        if "priority" in values:
            values["priority"] = self._require_choice(values["priority"], PRIORITIES, "Task priority")
        if "needs_review" in values:
            values["needs_review"] = int(bool(values["needs_review"]))
        if "title" in values and (not isinstance(values["title"], str) or not values["title"].strip()):
            raise ValueError("Task title is required")
        if "title" in values:
            values["title"] = values["title"].strip()
        if not values:
            return current
        values["updated_at"] = _now()
        assignments = ", ".join(f"{key}=?" for key in values)
        with self.lock:
            self.connection.execute(f"UPDATE tasks SET {assignments} WHERE id=?", (*values.values(), task_id))
            self.connection.commit()
        return self.get_task(task_id)

    def transition_task(self, task_id: str, status: str) -> dict:
        self._require_choice(status, TASK_STATUSES, "Task status")
        with self.lock:
            if self.connection.execute("UPDATE tasks SET status=?,updated_at=? WHERE id=?", (status, _now(), task_id)).rowcount != 1:
                raise KeyError(task_id)
            self.connection.commit()
        return self.get_task(task_id)

    def today(self, study_date: str, current_time: str | None = None) -> dict:
        tasks = self.list_tasks(study_date)
        open_tasks = [task for task in tasks if task["status"] not in {"completed", "skipped"}]
        active = next((task for task in open_tasks if task["status"] == "active"), None)
        priority_rank = {"high": 0, "medium": 1, "low": 2}
        planned = sorted(open_tasks, key=lambda task: (priority_rank[task["priority"]], task["due_at"] or "9999", task["start_time"] or "99:99"))
        current = active or (planned[0] if planned else None)
        current_index = next((index for index, task in enumerate(planned) if current and task["id"] == current["id"]), -1)
        return {
            "date": study_date, "current_time": current_time, "current_task": current,
            "next_tasks": [task for task in planned if not current or task["id"] != current["id"]][:2],
            "tasks": tasks,
            "completed_count": len([task for task in tasks if task["status"] == "completed"]),
            "remaining_count": len(open_tasks),
            "is_off_plan": bool(current and current.get("start_time") and current_time and current_time > current["start_time"]),
            "current_index": current_index,
        }

    def create_error_question(self, payload: dict) -> dict:
        if not isinstance(payload, dict) or not isinstance(payload.get("subject"), str) or not payload["subject"].strip():
            raise ValueError("Error question subject is required")
        priority = self._require_choice(payload.get("priority", "medium"), PRIORITIES, "Error question priority")
        mastery = self._require_choice(payload.get("mastery", "not_mastered"), MASTERY_STATES, "Mastery")
        now = _now()
        record = {
            "id": _id(), "subject": payload["subject"].strip(), "chapter": payload.get("chapter"), "title": payload.get("title"),
            "problem_text": payload.get("problem_text"), "work_text": payload.get("work_text"), "reasoning_text": payload.get("reasoning_text"),
            "correct_answer": payload.get("correct_answer"), "explanation": payload.get("explanation"), "notes": payload.get("notes"),
            "tags_json": _json(payload.get("tags", [])), "error_types_json": _json(payload.get("error_types", [])),
            "difficulty": payload.get("difficulty"), "priority": priority, "mastery": mastery,
            "next_review_date": payload.get("next_review_date") or date.today().isoformat(), "review_count": 0,
            "last_failed_at": None, "created_at": now, "updated_at": now,
        }
        with self.lock:
            self.connection.execute(
                """INSERT INTO error_questions VALUES(:id,:subject,:chapter,:title,:problem_text,:work_text,:reasoning_text,
                :correct_answer,:explanation,:notes,:tags_json,:error_types_json,:difficulty,:priority,:mastery,:next_review_date,
                :review_count,:last_failed_at,:created_at,:updated_at)""", record
            )
            self.connection.commit()
        return self.get_error_question(record["id"])

    def _format_error_question(self, record: dict) -> dict:
        record["tags"] = _parse_json(record.pop("tags_json"), [])
        record["error_types"] = _parse_json(record.pop("error_types_json"), [])
        return record

    def get_error_question(self, question_id: str) -> dict:
        record = self._one("SELECT * FROM error_questions WHERE id=?", (question_id,))
        if record is None:
            raise KeyError(question_id)
        return self._format_error_question(record)

    def list_error_questions(self, subject: str | None = None) -> list[dict]:
        rows = self._many("SELECT * FROM error_questions WHERE subject=? ORDER BY updated_at DESC", (subject,)) if subject else self._many("SELECT * FROM error_questions ORDER BY updated_at DESC")
        return [self._format_error_question(row) for row in rows]

    def update_error_question(self, question_id: str, changes: dict) -> dict:
        self.get_error_question(question_id)
        allowed = {"subject", "chapter", "title", "problem_text", "work_text", "reasoning_text", "correct_answer", "explanation", "notes", "difficulty", "priority", "mastery", "next_review_date", "tags", "error_types"}
        values = {key: value for key, value in changes.items() if key in allowed}
        if "priority" in values:
            values["priority"] = self._require_choice(values["priority"], PRIORITIES, "Error question priority")
        if "mastery" in values:
            values["mastery"] = self._require_choice(values["mastery"], MASTERY_STATES, "Mastery")
        for key in ("tags", "error_types"):
            if key in values:
                values[f"{key}_json"] = _json(values.pop(key))
        if not values:
            return self.get_error_question(question_id)
        values["updated_at"] = _now()
        assignments = ", ".join(f"{key}=?" for key in values)
        with self.lock:
            self.connection.execute(f"UPDATE error_questions SET {assignments} WHERE id=?", (*values.values(), question_id))
            self.connection.commit()
        return self.get_error_question(question_id)

    def daily_review(self, review_date: str, target_count: int = 5) -> list[dict]:
        rows = self._many(
            """SELECT * FROM error_questions WHERE subject='高等数学' AND mastery != 'mastered'
            AND next_review_date <= ? ORDER BY
            CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
            CASE mastery WHEN 'not_mastered' THEN 0 WHEN 'partial' THEN 1 ELSE 2 END,
            COALESCE(last_failed_at, '0000') ASC, next_review_date ASC LIMIT ?""",
            (review_date, target_count),
        )
        return [self._format_error_question(row) for row in rows]

    def record_review(self, question_id: str, reviewed_on: str, outcome: str, notes: str | None = None) -> dict:
        self._require_choice(outcome, REVIEW_OUTCOMES, "Review outcome")
        self.get_error_question(question_id)
        days = {"mastered": 14, "partial": 4, "cannot": 1, "careless": 3, "skipped": 1}[outcome]
        next_date = (date.fromisoformat(reviewed_on) + timedelta(days=days)).isoformat()
        mastery = {"mastered": "mastered", "partial": "partial", "cannot": "not_mastered", "careless": "partial", "skipped": "not_mastered"}[outcome]
        record = {"id": _id(), "error_question_id": question_id, "reviewed_on": reviewed_on, "outcome": outcome, "notes": notes, "next_review_date": next_date, "created_at": _now()}
        with self.lock:
            self.connection.execute("INSERT INTO review_records VALUES(:id,:error_question_id,:reviewed_on,:outcome,:notes,:next_review_date,:created_at)", record)
            self.connection.execute(
                """UPDATE error_questions SET mastery=?,next_review_date=?,review_count=review_count+1,
                last_failed_at=?,updated_at=? WHERE id=?""",
                (mastery, next_date, record["created_at"] if outcome in {"cannot", "careless"} else None, _now(), question_id),
            )
            self.connection.commit()
        return record

    def record_error_analysis(self, question_id: str, result: dict) -> dict:
        self.get_error_question(question_id)
        record = {
            "id": _id(),
            "error_question_id": question_id,
            "result_json": _json(result),
            "created_at": _now(),
        }
        with self.lock:
            self.connection.execute(
                "INSERT INTO error_analyses VALUES(:id,:error_question_id,:result_json,:created_at)",
                record,
            )
            self.connection.commit()
        return {"id": record["id"], "error_question_id": question_id, **result, "created_at": record["created_at"]}

    @staticmethod
    def _status_advice(mood: int | None, energy: int | None, stress: int | None, fatigued: bool, willing: bool | None) -> dict:
        if fatigued or energy == 1 or stress == 5 or willing is False:
            return {"level": "long_rest", "message": "建议休息 20 分钟，补水、走动后再决定是否继续。"}
        if energy == 2 or stress == 4:
            return {"level": "short_rest", "message": "建议休息 10 分钟，随后安排低难度复习或整理。"}
        if energy and energy >= 4 and stress and stress <= 2:
            return {"level": "high_intensity", "message": "当前适合安排需要专注的学习任务。"}
        return {"level": "normal_study", "message": "适合按计划完成普通学习任务，并在结束后记录状态。"}

    def record_status(self, payload: dict) -> dict:
        if not isinstance(payload, dict) or not isinstance(payload.get("recorded_on"), str):
            raise ValueError("Status recorded_on is required")
        for name in ("mood", "energy", "stress"):
            if payload.get(name) is not None and payload[name] not in {1, 2, 3, 4, 5}:
                raise ValueError(f"Status {name} must be 1 to 5")
        advice = self._status_advice(payload.get("mood"), payload.get("energy"), payload.get("stress"), bool(payload.get("fatigued")), payload.get("willing_to_continue"))
        record = {"id": _id(), "recorded_on": payload["recorded_on"], "mood": payload.get("mood"), "energy": payload.get("energy"), "stress": payload.get("stress"), "fatigued": int(bool(payload.get("fatigued"))), "willing_to_continue": None if payload.get("willing_to_continue") is None else int(bool(payload.get("willing_to_continue"))), "notes": payload.get("notes"), "advice_json": _json(advice), "created_at": _now()}
        with self.lock:
            self.connection.execute("INSERT INTO status_records VALUES(:id,:recorded_on,:mood,:energy,:stress,:fatigued,:willing_to_continue,:notes,:advice_json,:created_at)", record)
            self.connection.commit()
        record["fatigued"] = bool(record["fatigued"])
        record["advice"] = advice
        record.pop("advice_json")
        return record

    def list_status(self, recorded_on: str | None = None) -> list[dict]:
        rows = self._many(
            "SELECT * FROM status_records WHERE recorded_on=? ORDER BY created_at DESC",
            (recorded_on,),
        ) if recorded_on else self._many("SELECT * FROM status_records ORDER BY created_at DESC")
        for row in rows:
            row["fatigued"] = bool(row["fatigued"])
            row["willing_to_continue"] = None if row["willing_to_continue"] is None else bool(row["willing_to_continue"])
            row["advice"] = _parse_json(row.pop("advice_json"), {})
        return rows

    def create_chat(self, payload: dict) -> dict:
        title = payload.get("title") if isinstance(payload, dict) else None
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Chat title is required")
        record = {"id": _id(), "title": title.strip(), "created_at": _now(), "updated_at": _now()}
        with self.lock:
            self.connection.execute("INSERT INTO chats VALUES(:id,:title,:created_at,:updated_at)", record)
            self.connection.commit()
        return record

    def add_chat_message(self, chat_id: str, payload: dict) -> dict:
        if not isinstance(payload, dict) or payload.get("role") not in {"user", "assistant", "system"} or not isinstance(payload.get("content"), str) or not payload["content"].strip():
            raise ValueError("Chat message role and content are required")
        if self._one("SELECT id FROM chats WHERE id=?", (chat_id,)) is None:
            raise KeyError(chat_id)
        record = {"id": _id(), "chat_id": chat_id, "role": payload["role"], "content": payload["content"].strip(), "link_type": payload.get("link_type"), "link_id": payload.get("link_id"), "created_at": _now()}
        with self.lock:
            self.connection.execute("INSERT INTO chat_messages VALUES(:id,:chat_id,:role,:content,:link_type,:link_id,:created_at)", record)
            self.connection.execute("UPDATE chats SET updated_at=? WHERE id=?", (_now(), chat_id))
            self.connection.commit()
        return record

    def list_chats(self, query: str | None = None) -> list[dict]:
        if query:
            return self._many(
                """SELECT DISTINCT chats.* FROM chats LEFT JOIN chat_messages ON chats.id=chat_messages.chat_id
                WHERE chats.title LIKE ? OR chat_messages.content LIKE ? ORDER BY chats.updated_at DESC""",
                (f"%{query}%", f"%{query}%"),
            )
        return self._many("SELECT * FROM chats ORDER BY updated_at DESC")

    def list_chat_messages(self, chat_id: str) -> list[dict]:
        if self._one("SELECT id FROM chats WHERE id=?", (chat_id,)) is None:
            raise KeyError(chat_id)
        return self._many("SELECT * FROM chat_messages WHERE chat_id=? ORDER BY created_at", (chat_id,))

    def statistics(self) -> dict:
        subjects = self._many("SELECT subject, COUNT(*) AS count FROM error_questions GROUP BY subject ORDER BY count DESC")
        chapters = self._many("SELECT COALESCE(chapter, '未分类') AS chapter, COUNT(*) AS count FROM error_questions GROUP BY chapter ORDER BY count DESC")
        error_types: dict[str, int] = {}
        for row in self._many("SELECT error_types_json FROM error_questions"):
            for error_type in _parse_json(row["error_types_json"], []):
                error_types[error_type] = error_types.get(error_type, 0) + 1
        return {"by_subject": subjects, "by_chapter": chapters, "by_error_type": [{"name": key, "count": value} for key, value in sorted(error_types.items())]}

    def get_ai_settings(self) -> dict:
        record = self._one("SELECT base_url,protocol,model,timeout_seconds,updated_at FROM ai_settings WHERE id=1")
        return record or {
            "base_url": "",
            "protocol": "chat_completions",
            "model": "",
            "timeout_seconds": DEFAULT_AI_TIMEOUT_SECONDS,
            "updated_at": None,
        }

    def validate_ai_settings(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise ValueError("AI settings must be an object")
        if "api_key" in payload:
            raise ValueError("API key must not be stored in Learning OS data")
        current = self.get_ai_settings()
        values = {
            "base_url": payload.get("base_url", current["base_url"]),
            "protocol": payload.get("protocol", current["protocol"]),
            "model": payload.get("model", current["model"]),
            "timeout_seconds": payload.get("timeout_seconds", current["timeout_seconds"]),
        }
        if not isinstance(values["base_url"], str) or not values["base_url"].strip():
            raise ValueError("AI base_url is required")
        parsed = urlparse(values["base_url"].strip())
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("AI base_url must use HTTPS")
        values["base_url"] = values["base_url"].strip()
        values["protocol"] = self._require_choice(values["protocol"], AI_PROTOCOLS, "AI protocol")
        if not isinstance(values["model"], str) or not values["model"].strip():
            raise ValueError("AI model is required")
        values["model"] = values["model"].strip()
        if isinstance(values["timeout_seconds"], bool):
            raise ValueError("AI timeout must be an integer")
        try:
            values["timeout_seconds"] = int(values["timeout_seconds"])
        except (TypeError, ValueError) as error:
            raise ValueError("AI timeout must be an integer") from error
        if not MIN_AI_TIMEOUT_SECONDS <= values["timeout_seconds"] <= MAX_AI_TIMEOUT_SECONDS:
            raise ValueError(
                f"AI timeout must be {MIN_AI_TIMEOUT_SECONDS} to {MAX_AI_TIMEOUT_SECONDS} seconds"
            )
        return values

    def update_ai_settings(self, payload: dict) -> dict:
        values = self.validate_ai_settings(payload)
        values["updated_at"] = _now()
        with self.lock:
            self.connection.execute(
                """INSERT INTO ai_settings(id,base_url,protocol,model,timeout_seconds,updated_at)
                VALUES(1,:base_url,:protocol,:model,:timeout_seconds,:updated_at)
                ON CONFLICT(id) DO UPDATE SET base_url=excluded.base_url,
                  protocol=excluded.protocol,model=excluded.model,
                  timeout_seconds=excluded.timeout_seconds,updated_at=excluded.updated_at""",
                values,
            )
            self.connection.commit()
        return self.get_ai_settings()

    def close(self):
        self.connection.close()
