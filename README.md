# European Higher Education Data Platform (EHEDP)

## Purpose of the Solution
The **European Higher Education Data Platform (EHEDP)** is an enterprise-grade data platform engineered to ingest, harmonize, store, and analyze higher education metrics across European nations.

Due to the lack of standardized Grade Point Average (GPA) systems across the European Higher Education Area (EHEA), EHEDP replaces GPA with standardized proxy metrics: academic completion rates, yearly student volume, graduate counts by ISCED-F degree fields, and credit progression.

To support high-concurrency ingestion for over 3,500 Higher Education Institutions (HEIs) across 40 countries, EHEDP implements **PostgreSQL List Partitioning** mapped strictly to university entities (`1 Thread = 1 University Partition`). This eliminates table lock contention and database lock deadlocks during parallel ingestion.

---

## Tech Stack
- **Database Engine**: PostgreSQL 16+ (Declarative List Partitioning, PL/pgSQL stored routines)
- **Connection Middleware**: PgBouncer 1.21+ (Transaction-level connection pooling on Port 6432)
- **Ingestion & Orchestration Engine**: Python 3.11+ (`psycopg3`, `psycopg_pool`, `concurrent.futures.ThreadPoolExecutor`)
- **Container Infrastructure**: Docker & Docker Compose
- **Analytics & BI Layer**: Power BI Desktop (Star Schema Model, DAX Engine, DirectQuery/Import/Python M Routing)

---

## Installation Guide

### Prerequisites
- Docker Engine & Docker Compose
- Python 3.11+

### Installation Steps

1. **Clone the Repository**:
   ```bash
   git clone <repository_url>
   cd <repository_directory>
   ```

2. **Set Up Python Dependencies**:
   ```bash
   pip install "psycopg[binary]" "psycopg-pool[binary]" pytest
   ```

3. **Deploy Infrastructure via Docker Compose**:
   ```bash
   docker compose up -d
   ```
   This spins up:
   - PostgreSQL 16 on port `5432`
   - PgBouncer transaction-mode pooler on port `6432`

4. **Initialize Database Schema**:
   Connect to PostgreSQL and run `init_schema.sql`:
   ```bash
   psql -h localhost -p 5432 -U postgres -d edu_metrics -f init_schema.sql
   ```

---

## User Manual & Operational Runbook

### Step 1: Execute Partition Management
Audit registered universities and ensure that dedicated physical table partitions exist for every `uni_id`:
```bash
python manage_partitions.py
```
*Note: The automatic trigger `trg_auto_create_university_partition` will also dynamically create new partitions whenever a new university is inserted into `university`.*

### Step 2: Execute High-Throughput Parallel Ingestion Pipeline
Launch multi-threaded parallel data loading through PgBouncer:
```bash
python ingest_engine.py
```
By default, this connects to `postgresql://postgres:postgrespassword@localhost:6432/edu_metrics` using a connection pool and processes data across worker threads.

### Step 3: Run Automated Test Suite
To run the automated mock/unit test suite:
```bash
PYTHONPATH=. pytest tests/
```

### Step 4: Configure Power BI Dashboard
1. Open Power BI Desktop and import the dynamic data selector query in `power_bi/dynamic_data_selector.m`.
2. Configure parameter `DataSourceType` to `'DB'`, `'CSV'`, or `'PYTHON'`.
3. Load the DAX measures defined in `power_bi/dax_measures.dax` into your Star Schema report model.
