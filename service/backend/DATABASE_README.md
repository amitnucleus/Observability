# PNOG Backend — Database Guide

## Overview

The PNOG backend uses **PostgreSQL 15** running inside a Docker container. All uploaded files create job records in the `jobs` table, and the processing pipeline updates their status as they move through the system.

---

## 1. Database Connection

### Find your credentials

```bash
# From project root
cat .env | grep POSTGRES

# Or check inside the container
docker compose exec postgres env | grep POSTGRES
```

### Connect via command line (psql)

```bash
# Connect to the database
docker compose exec postgres psql -U <POSTGRES_USER> -d <POSTGRES_DB>

# Example
docker compose exec postgres psql -U pnog_user -d pnog_user
```



## 2. Database Schema

### Jobs Table Structure

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key (auto-generated) |
| `filename` | VARCHAR | Original uploaded filename |
| `status` | VARCHAR | pending → processing → done / error |
| `result` | TEXT | Processing result or error message |
| `file_size` | INTEGER | File size in bytes |
| `created_at` | TIMESTAMP | When the job was created |
| `completed_at` | TIMESTAMP | When processing finished (nullable) |



### Status Flow

```
Upload → pending → processing → done
                              → error
```

---

## 3. Checking Data — psql Commands

### Inside psql

```sql
-- List all databases
\l

-- List all tables
\dt

-- Show table structure (columns, types)
\d jobs

-- View all jobs
SELECT * FROM jobs ORDER BY created_at DESC;

-- View recent 10 jobs
SELECT id, filename, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 10;

-- Count jobs by status
SELECT status, COUNT(*) FROM jobs GROUP BY status;

-- Find pending jobs
SELECT * FROM jobs WHERE status = 'pending';

-- Find completed jobs
SELECT * FROM jobs WHERE status = 'done';

-- Find failed jobs
SELECT id, filename, result FROM jobs WHERE status = 'error';

-- Check if specific file was uploaded
SELECT * FROM jobs WHERE filename = 'graph_clean.xlsx';

-- Check processing time
SELECT id, filename, completed_at - created_at AS duration
FROM jobs WHERE status = 'done' ORDER BY created_at DESC;

-- Exit psql
\q
```

### Quick one-liners (PowerShell — no need to enter psql)

```powershell
# List tables
docker compose exec postgres psql -U <USER> -d <DB> -c "\dt"

# View all jobs
docker compose exec postgres psql -U <USER> -d <DB> -c "SELECT * FROM jobs ORDER BY created_at DESC;"

# Count by status
docker compose exec postgres psql -U <USER> -d <DB> -c "SELECT status, COUNT(*) FROM jobs GROUP BY status;"

# Table structure
docker compose exec postgres psql -U <USER> -d <DB> -c "\d jobs"
```

---

## 4. Data Types & Verification

### Check column data types

```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'jobs'
ORDER BY ordinal_position;
```

### Check table size

```sql
SELECT
    pg_size_pretty(pg_total_relation_size('jobs')) AS total_size,
    pg_size_pretty(pg_relation_size('jobs')) AS data_size;
```

### Count total rows

```sql
SELECT COUNT(*) FROM jobs;
```

### Check for NULL values

```sql
SELECT
    COUNT(*) AS total,
    COUNT(filename) AS has_filename,
    COUNT(status) AS has_status,
    COUNT(result) AS has_result,
    COUNT(file_size) AS has_file_size,
    COUNT(completed_at) AS has_completed_at
FROM jobs;
```

### Unique filenames uploaded

```sql
SELECT filename, COUNT(*) AS uploads FROM jobs GROUP BY filename ORDER BY uploads DESC;
```

### Data integrity checks

```sql
-- Invalid status values
SELECT * FROM jobs WHERE status NOT IN ('pending', 'processing', 'done', 'error');

-- Completed but missing timestamp
SELECT * FROM jobs WHERE status = 'done' AND completed_at IS NULL;
```

---

## 5. Common Operations

```sql
-- Delete all pending jobs
DELETE FROM jobs WHERE status = 'pending';

-- Reset stuck job back to pending
UPDATE jobs SET status = 'pending', result = NULL WHERE id = '<job-uuid>';

-- Delete all jobs (fresh start)
TRUNCATE TABLE jobs;
```

### Export to CSV

```bash
docker compose exec postgres psql -U <USER> -d <DB> \
  -c "COPY (SELECT * FROM jobs ORDER BY created_at DESC) TO STDOUT WITH CSV HEADER" \
  > jobs_export.csv
```

---

## 6. Troubleshooting

| Problem | Fix |
|---------|-----|
| "role does not exist" | Wrong username. Run: `docker compose exec postgres env \| grep POSTGRES_USER` |
| "database does not exist" | DB not created. Run: `docker compose exec postgres psql -U postgres -c "CREATE DATABASE <db>;"` |
| Jobs stuck at "pending" | Celery not running. Run: `docker compose logs celery --tail=20` |
| Jobs stuck at "processing" | Celery crashed. Reset: `UPDATE jobs SET status='pending' WHERE status='processing';` then `docker compose restart celery` |
| Cannot connect | Check: `docker compose ps postgres` and `docker compose logs postgres --tail=10` |

---

## 7. SQLAlchemy Model Reference

File: `app/models/job.py`

```python
class Job(Base):
    __tablename__ = "jobs"

    id           = Column(UUID, primary_key=True, default=uuid.uuid4)
    filename     = Column(String, nullable=False)
    status       = Column(String, default="pending")
    result       = Column(Text, nullable=True)
    file_size    = Column(Integer, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
```

Database config: `app/database.py`

```python
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession)
Base = declarative_base()
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Enter psql | `docker compose exec postgres psql -U <USER> -d <DB>` |
| List tables | `\dt` |
| Describe table | `\d jobs` |
| All jobs | `SELECT * FROM jobs ORDER BY created_at DESC;` |
| Count by status | `SELECT status, COUNT(*) FROM jobs GROUP BY status;` |
| Column types | `SELECT column_name, data_type FROM information_schema.columns WHERE table_name='jobs';` |
| Exit | `\q` |
