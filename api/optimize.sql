-- =====================================================================
-- Tối ưu hiệu năng cho recommend — chạy sau khi đã load dữ liệu
--   docker exec -i dss-postgres psql -U dss -d dss_jobs < api/optimize.sql
-- =====================================================================
\timing on

-- 1) Thống kê đầy đủ để planner chọn đúng index
ANALYZE user_skills;
ANALYZE job_skills;
ANALYZE apps;
ANALYZE jobs;

-- 2) Index bao phủ: cho phép Index Only Scan khi join skill -> job
--    (skill, job_id) thay vì chỉ (skill) để không phải đọc heap
DROP INDEX IF EXISTS idx_job_skills_skill_job;
CREATE INDEX idx_job_skills_skill_job ON job_skills (skill, job_id);

-- 3) Index cho lọc job theo employer (dùng ở /api/clients/{id})
DROP INDEX IF EXISTS idx_jobs_employer_title;
CREATE INDEX idx_jobs_employer_title ON jobs (employer) INCLUDE (title, occupation);

-- 4) Index cho đếm app theo job
DROP INDEX IF EXISTS idx_apps_job_user;
CREATE INDEX idx_apps_job_user ON apps (job_id) INCLUDE (user_id);

-- 5) Materialized view: skill -> danh sách job (giảm join 2,6M dòng mỗi lần)
DROP MATERIALIZED VIEW IF EXISTS mv_skill_jobs;
CREATE MATERIALIZED VIEW mv_skill_jobs AS
SELECT skill, job_id
FROM job_skills;
CREATE INDEX idx_mv_skill_jobs_skill ON mv_skill_jobs (skill, job_id);

ANALYZE mv_skill_jobs;

-- 6) Cấu hình runtime cho session đọc nhiều
ALTER DATABASE dss_jobs SET work_mem = '256MB';
ALTER DATABASE dss_jobs SET random_page_cost = 1.1;
ALTER DATABASE dss_jobs SET effective_cache_size = '4GB';
ALTER DATABASE dss_jobs SET max_parallel_workers_per_gather = 4;

\d+
SELECT 'optimize xong' AS status;
