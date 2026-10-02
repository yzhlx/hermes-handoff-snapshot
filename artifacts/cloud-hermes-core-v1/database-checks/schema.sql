-- Cloud Hermes Core V1 — schema dump
-- source: F:\Users\user\Documents\learning os-worktrees\cloud-hermes-core-v1\work\smoke-data\hermes_cloud.db

-- index: idx_cand_status
CREATE INDEX idx_cand_status ON memory_candidates(status);

-- index: idx_conv_user
CREATE INDEX idx_conv_user ON conversations(user_id);

-- index: idx_events_agg
CREATE INDEX idx_events_agg ON events(aggregate_type, aggregate_id, sequence);

-- index: idx_events_corr
CREATE INDEX idx_events_corr ON events(correlation_id);

-- index: idx_exec_idem
CREATE INDEX idx_exec_idem ON execution_commands(idempotency_key);

-- index: idx_exec_status
CREATE INDEX idx_exec_status ON execution_commands(status, device_id);

-- index: idx_login_attempts_key
CREATE INDEX idx_login_attempts_key ON login_attempts(username, ip, attempted_at);

-- index: idx_memory_ns
CREATE INDEX idx_memory_ns ON memory_items(namespace, status);

-- index: idx_msg_conv
CREATE INDEX idx_msg_conv ON messages(conversation_id, created_at);

-- index: idx_runs_conv
CREATE INDEX idx_runs_conv ON hermes_runs(conversation_id);

-- index: idx_runs_user
CREATE INDEX idx_runs_user ON hermes_runs(user_id);

-- index: idx_sessions_token
CREATE INDEX idx_sessions_token ON sessions(token_hash);

-- index: idx_sessions_user
CREATE INDEX idx_sessions_user ON sessions(user_id);

-- index: idx_tasks_user
CREATE INDEX idx_tasks_user ON tasks(user_id);

-- table: conversations
CREATE TABLE conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT,
            role_id TEXT NOT NULL DEFAULT 'master',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

-- table: devices
CREATE TABLE devices (
            device_id TEXT PRIMARY KEY,
            user_id TEXT,
            client_type TEXT,
            client_version TEXT,
            last_seen TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

-- table: events
CREATE TABLE events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                aggregate_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                actor TEXT,
                source TEXT,
                idempotency_key TEXT,
                causation_id TEXT,
                correlation_id TEXT,
                payload_version INTEGER NOT NULL DEFAULT 1,
                payload_json TEXT NOT NULL,
                artifact_refs_json TEXT,
                metadata_json TEXT
            );

-- table: execution_commands
CREATE TABLE execution_commands (
            id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            command_type TEXT NOT NULL,
            payload_json TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            idempotency_key TEXT,
            lease_token TEXT,
            lease_expires_at TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            result_json TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        );

-- table: execution_nodes
CREATE TABLE execution_nodes (
            device_id TEXT PRIMARY KEY,
            user_id TEXT,
            status TEXT NOT NULL DEFAULT 'offline',
            capabilities_json TEXT,
            last_seen TEXT,
            registered_at TEXT NOT NULL
        );

-- table: hermes_runs
CREATE TABLE hermes_runs (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            user_id TEXT,
            role_id TEXT NOT NULL,
            status TEXT NOT NULL,
            context_retrieval_performed INTEGER NOT NULL DEFAULT 0,
            memory_count INTEGER NOT NULL DEFAULT 0,
            provider_performed INTEGER NOT NULL DEFAULT 0,
            provider_name TEXT,
            provider_model TEXT,
            event_count INTEGER NOT NULL DEFAULT 0,
            memory_candidate_count INTEGER NOT NULL DEFAULT 0,
            tool_calls_json TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            correlation_id TEXT
        );

-- table: idempotency_records
CREATE TABLE idempotency_records (
            key TEXT PRIMARY KEY,
            response_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

-- table: login_attempts
CREATE TABLE login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            ip TEXT,
            attempted_at TEXT NOT NULL,
            success INTEGER NOT NULL DEFAULT 0
        );

-- table: memory_candidates
CREATE TABLE memory_candidates (
            id TEXT PRIMARY KEY,
            candidate_type TEXT NOT NULL,
            content TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.5,
            source_message_ids_json TEXT,
            role_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            promoted_item_id TEXT,
            reason TEXT
        );

-- table: memory_items
CREATE TABLE memory_items (
            id TEXT PRIMARY KEY,
            namespace TEXT NOT NULL,
            kind TEXT NOT NULL,
            content TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.5,
            source_message_ids_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        );

-- table: messages
CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            hermes_run_id TEXT,
            created_at TEXT NOT NULL,
            metadata_json TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

-- table: schema_migrations
CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);

-- table: sessions
CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            device_id TEXT,
            csrf_token TEXT,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

-- table: sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);

-- table: tasks
CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

-- table: tool_runs
CREATE TABLE tool_runs (
            id TEXT PRIMARY KEY,
            hermes_run_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            status TEXT NOT NULL,
            input_json TEXT,
            output_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (hermes_run_id) REFERENCES hermes_runs(id)
        );

-- table: users
CREATE TABLE users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            created_at TEXT NOT NULL,
            admin_initialized INTEGER NOT NULL DEFAULT 0
        );

-- trigger: events_no_delete
CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;

-- trigger: events_no_update
CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;

