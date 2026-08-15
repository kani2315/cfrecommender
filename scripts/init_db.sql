-- Step 6 — PostgreSQL schema
-- This is auto‑created by SQLAlchemy's create_tables(),
-- but provided here as reference / for manual setup.

CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(50) UNIQUE NOT NULL,
    skill_level FLOAT DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS problems (
    id         SERIAL PRIMARY KEY,
    difficulty VARCHAR(10) NOT NULL,
    topic      VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS submissions (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    problem_id   INTEGER NOT NULL REFERENCES problems(id),
    solved       BOOLEAN NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- indexes for common queries
CREATE INDEX IF NOT EXISTS idx_submissions_user    ON submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_submissions_problem ON submissions(problem_id);
CREATE INDEX IF NOT EXISTS idx_problems_topic      ON problems(topic);
