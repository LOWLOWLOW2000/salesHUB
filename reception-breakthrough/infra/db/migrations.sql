PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS call_sessions (
    id TEXT PRIMARY KEY,
    lead_id TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('AI', 'HUMAN')),
    started_at TEXT NOT NULL,
    ended_at TEXT,
    final_state_id TEXT CHECK (
        final_state_id IN (
            'S0', 'S1', 'S2', 'S3', 'S4', 'S5',
            'S6', 'S7', 'S8', 'S9', 'S10', 'S11'
        )
    ),
    outcome_id TEXT CHECK (
        outcome_id IN (
            'OUT_CONNECTED',
            'OUT_REJECTED',
            'OUT_ABSENT',
            'OUT_NOISE'
        )
    ),
    rejection_reason TEXT,
    callback_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_call_sessions_lead_id
    ON call_sessions (lead_id);

CREATE INDEX IF NOT EXISTS idx_call_sessions_outcome_id
    ON call_sessions (outcome_id);

CREATE TABLE IF NOT EXISTS call_recordings (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    audio_path TEXT NOT NULL UNIQUE,
    duration_sec INTEGER CHECK (duration_sec IS NULL OR duration_sec >= 0),
    audio_hash TEXT,
    source_kind TEXT NOT NULL DEFAULT 'file',
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES call_sessions (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_call_recordings_session_id
    ON call_recordings (session_id);

CREATE TABLE IF NOT EXISTS transcripts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    recording_id TEXT,
    speaker TEXT NOT NULL,
    text TEXT NOT NULL,
    start_time_ms INTEGER CHECK (start_time_ms IS NULL OR start_time_ms >= 0),
    end_time_ms INTEGER CHECK (end_time_ms IS NULL OR end_time_ms >= 0),
    source_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES call_sessions (id) ON DELETE CASCADE,
    FOREIGN KEY (recording_id) REFERENCES call_recordings (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_transcripts_session_id
    ON transcripts (session_id);

CREATE INDEX IF NOT EXISTS idx_transcripts_recording_id
    ON transcripts (recording_id);

CREATE TABLE IF NOT EXISTS intent_labels (
    id TEXT PRIMARY KEY,
    transcript_id TEXT NOT NULL,
    predicted_intent TEXT NOT NULL,
    correct_intent TEXT,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    reviewed_by TEXT,
    reviewed_at TEXT,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transcript_id) REFERENCES transcripts (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_intent_labels_transcript_id
    ON intent_labels (transcript_id);

CREATE INDEX IF NOT EXISTS idx_intent_labels_predicted_intent
    ON intent_labels (predicted_intent);

CREATE TABLE IF NOT EXISTS state_transitions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    seq INTEGER NOT NULL CHECK (seq >= 0),
    from_state TEXT NOT NULL CHECK (
        from_state IN (
            'S0', 'S1', 'S2', 'S3', 'S4', 'S5',
            'S6', 'S7', 'S8', 'S9', 'S10', 'S11'
        )
    ),
    to_state TEXT NOT NULL CHECK (
        to_state IN (
            'S0', 'S1', 'S2', 'S3', 'S4', 'S5',
            'S6', 'S7', 'S8', 'S9', 'S10', 'S11'
        )
    ),
    input_kind TEXT NOT NULL CHECK (input_kind IN ('intent', 'event')),
    input_id TEXT NOT NULL,
    response_template_id TEXT,
    at TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('AI', 'HUMAN')),
    extra_json TEXT,
    FOREIGN KEY (session_id) REFERENCES call_sessions (id) ON DELETE CASCADE,
    UNIQUE (session_id, seq)
);

CREATE INDEX IF NOT EXISTS idx_state_transitions_session_id
    ON state_transitions (session_id);

CREATE INDEX IF NOT EXISTS idx_state_transitions_states
    ON state_transitions (from_state, to_state);

CREATE TABLE IF NOT EXISTS outcomes (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    outcome_id TEXT NOT NULL CHECK (
        outcome_id IN (
            'OUT_CONNECTED',
            'OUT_REJECTED',
            'OUT_ABSENT',
            'OUT_NOISE'
        )
    ),
    final_state_id TEXT NOT NULL CHECK (
        final_state_id IN (
            'S0', 'S1', 'S2', 'S3', 'S4', 'S5',
            'S6', 'S7', 'S8', 'S9', 'S10', 'S11'
        )
    ),
    rejection_reason TEXT,
    callback_at TEXT,
    last_input_kind TEXT CHECK (last_input_kind IN ('intent', 'event')),
    last_input_id TEXT,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES call_sessions (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_outcomes_outcome_id
    ON outcomes (outcome_id);

CREATE TABLE IF NOT EXISTS failure_cases (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    outcome_id TEXT NOT NULL CHECK (
        outcome_id IN (
            'OUT_CONNECTED',
            'OUT_REJECTED',
            'OUT_ABSENT',
            'OUT_NOISE'
        )
    ),
    failure_state_id TEXT CHECK (
        failure_state_id IN (
            'S0', 'S1', 'S2', 'S3', 'S4', 'S5',
            'S6', 'S7', 'S8', 'S9', 'S10', 'S11'
        )
    ),
    last_input_kind TEXT CHECK (last_input_kind IN ('intent', 'event')),
    last_input_id TEXT,
    summary TEXT,
    extracted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES call_sessions (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_failure_cases_session_id
    ON failure_cases (session_id);

CREATE TABLE IF NOT EXISTS template_variants (
    id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL,
    variant_id TEXT NOT NULL UNIQUE,
    body_text TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    retired_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_template_variants_template_id
    ON template_variants (template_id);

CREATE TABLE IF NOT EXISTS metric_snapshots (
    id TEXT PRIMARY KEY,
    metric_date TEXT NOT NULL,
    scope_type TEXT NOT NULL CHECK (scope_type IN ('session', 'intent', 'template')),
    scope_key TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    meta_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (metric_date, scope_type, scope_key, metric_name)
);

CREATE INDEX IF NOT EXISTS idx_metric_snapshots_scope
    ON metric_snapshots (metric_date, scope_type, scope_key);
