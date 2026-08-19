-- 1. Master University Table (Unpartitioned)
CREATE TABLE IF NOT EXISTS university (
    uni_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country_code VARCHAR(5) NOT NULL
);

-- 2. Degree Level Reference Table
CREATE TABLE IF NOT EXISTS degree_level (
    degree_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    level_name VARCHAR(50) NOT NULL UNIQUE
);

-- Seed Default Degree Levels
INSERT INTO degree_level (level_name)
VALUES ('Bachelor'), ('Master'), ('PhD')
ON CONFLICT (level_name) DO NOTHING;

-- 3. Course Type Table
CREATE TABLE IF NOT EXISTS course_type (
    course_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uni_id INT NOT NULL,
    degree_id INT NOT NULL REFERENCES degree_level(degree_id),
    course_name VARCHAR(255) NOT NULL,
    CONSTRAINT uq_uni_course UNIQUE (uni_id, course_name, degree_id)
);

-- 4. Audit Log Table
CREATE TABLE IF NOT EXISTS ingestion_audit_log (
    log_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    uni_id INT NOT NULL,
    academic_year INT NOT NULL,
    records_processed INT DEFAULT 0,
    status VARCHAR(50) NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Partitioned Yearly Metrics Table (Parent)
CREATE TABLE IF NOT EXISTS yearly_metrics (
    metric_id INT GENERATED ALWAYS AS IDENTITY,
    uni_id INT NOT NULL,
    course_id INT NOT NULL,
    academic_year INT NOT NULL,
    attendees INT DEFAULT 0,
    graduates INT DEFAULT 0,
    PRIMARY KEY (metric_id, uni_id),
    CONSTRAINT uq_course_year UNIQUE (course_id, academic_year, uni_id)
) PARTITION BY LIST (uni_id);

-- Seed Initial Sample Universities
INSERT INTO university (name, country_code) VALUES
('Technical University of Munich', 'DE'),
('Ludwig Maximilian University of Munich', 'DE'),
('ETH Zurich', 'CH'),
('University of Oxford', 'GB'),
('Delft University of Technology', 'NL')
ON CONFLICT DO NOTHING;

-- 6. Idempotent Upsert Function (PL/pgSQL Procedure)
CREATE OR REPLACE FUNCTION sp_upsert_yearly_metrics(
    p_uni_id INT,
    p_course_id INT,
    p_year INT,
    p_attendees INT,
    p_graduates INT
) RETURNS VOID AS $$
BEGIN
    INSERT INTO yearly_metrics (uni_id, course_id, academic_year, attendees, graduates)
    VALUES (p_uni_id, p_course_id, p_year, p_attendees, p_graduates)
    ON CONFLICT (course_id, academic_year, uni_id)
    DO UPDATE SET
        attendees = EXCLUDED.attendees,
        graduates = EXCLUDED.graduates;
END;
$$ LANGUAGE plpgsql;

-- 7. Automatic Partition Creation Trigger Function
CREATE OR REPLACE FUNCTION trg_auto_create_university_partition()
RETURNS TRIGGER AS $$
DECLARE
    v_partition_name TEXT;
BEGIN
    v_partition_name := 'yearly_metrics_uni_' || NEW.uni_id;

    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF yearly_metrics FOR VALUES IN (%L);',
        v_partition_name,
        NEW.uni_id
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_university_after_insert ON university;
CREATE TRIGGER trg_university_after_insert
AFTER INSERT ON university
FOR EACH ROW
EXECUTE FUNCTION trg_auto_create_university_partition();
