-- =====================================================================
-- schema.sql — PostgreSQL 14+ cho hệ gợi ý việc làm GNN + Federated Learning
-- Tạo DB:  createdb dss_jobs
-- Nạp:     psql -d dss_jobs -f schema.sql
-- =====================================================================
BEGIN;

-- ---------- dữ liệu gốc ----------
CREATE TABLE IF NOT EXISTS users (
    user_id    BIGINT PRIMARY KEY,
    state      TEXT,
    degree     TEXT,
    years_exp  INTEGER
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id      BIGINT PRIMARY KEY,
    title       TEXT,
    employer    TEXT,
    occupation  TEXT,
    city        TEXT,
    state       TEXT
);

CREATE TABLE IF NOT EXISTS apps (
    user_id     BIGINT      NOT NULL,
    job_id      BIGINT      NOT NULL,
    applied_at  TIMESTAMPTZ,
    PRIMARY KEY (user_id, job_id)
);

-- ---------- client FL = nhà tuyển dụng ----------
CREATE TABLE IF NOT EXISTS employers (
    client_id  INTEGER PRIMARY KEY,
    name       TEXT,
    n_apps     INTEGER,
    n_users    INTEGER,
    n_jobs     INTEGER
);

-- ---------- lớp skill (suy qua nghề, ghi rõ trong meta.json) ----------
CREATE TABLE IF NOT EXISTS job_skills (
    job_id  BIGINT NOT NULL,
    skill   TEXT   NOT NULL,
    PRIMARY KEY (job_id, skill)
);

CREATE TABLE IF NOT EXISTS user_skills (
    user_id  BIGINT NOT NULL,
    skill    TEXT   NOT NULL,
    PRIMARY KEY (user_id, skill)
);

-- ---------- theo dõi huấn luyện ----------
CREATE TABLE IF NOT EXISTS train_runs (
    run_id      UUID PRIMARY KEY,
    started_at  TIMESTAMPTZ,
    n_clients   INTEGER,
    rounds      INTEGER,
    status      TEXT
);

-- t7: cột phục vụ dừng run phía server (dừng giữa chừng).
-- Dùng ALTER ... IF NOT EXISTS để DB đã tạo từ schema cũ vẫn nâng cấp được.
ALTER TABLE train_runs ADD COLUMN IF NOT EXISTS stopped_at_round INTEGER;
ALTER TABLE train_runs ADD COLUMN IF NOT EXISTS ended_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS round_metrics (
    run_id    UUID NOT NULL REFERENCES train_runs(run_id) ON DELETE CASCADE,
    round     INTEGER NOT NULL,
    recall20  DOUBLE PRECISION,
    ndcg20    DOUBLE PRECISION,
    mrr20     DOUBLE PRECISION,
    loss      DOUBLE PRECISION,
    PRIMARY KEY (run_id, round)
);

CREATE TABLE IF NOT EXISTS node_latency (
    run_id      UUID NOT NULL REFERENCES train_runs(run_id) ON DELETE CASCADE,
    round       INTEGER NOT NULL,
    client_id   INTEGER NOT NULL,
    latency_ms  DOUBLE PRECISION,
    bytes_up    BIGINT,
    bytes_down  BIGINT,
    PRIMARY KEY (run_id, round, client_id)
);

-- ---------- index bắt buộc ----------
CREATE INDEX IF NOT EXISTS idx_apps_user        ON apps(user_id);
CREATE INDEX IF NOT EXISTS idx_apps_job         ON apps(job_id);
CREATE INDEX IF NOT EXISTS idx_node_latency_run ON node_latency(run_id, round);
-- index phụ phục vụ truy vấn UI
CREATE INDEX IF NOT EXISTS idx_jobs_employer     ON jobs(employer);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill  ON job_skills(skill);
CREATE INDEX IF NOT EXISTS idx_user_skills_skill ON user_skills(skill);
-- bắt buộc cho /api/recommend: tra skill của 1 job và skill của 1 user.
-- Thiếu 2 index này thì Postgres seq-scan 2,6M / 18M dòng mỗi lần gợi ý.
CREATE INDEX IF NOT EXISTS idx_job_skills_job    ON job_skills(job_id);
CREATE INDEX IF NOT EXISTS idx_user_skills_user  ON user_skills(user_id);
CREATE INDEX IF NOT EXISTS idx_train_runs_started ON train_runs(started_at DESC);

COMMIT;
