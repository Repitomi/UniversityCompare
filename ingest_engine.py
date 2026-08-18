import concurrent.futures
from psycopg_pool import ConnectionPool
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(threadName)s - %(message)s")

DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgrespassword@localhost:6432/edu_metrics")

def get_pool(db_uri: str = DB_URI) -> ConnectionPool:
    return ConnectionPool(conninfo=db_uri, min_size=2, max_size=25, open=True)

def worker_load_university(pool: ConnectionPool, uni_id: int, target_year: int) -> str:
    """
    Worker task: Processes ONE university exclusively on a dedicated thread.
    Executes atomic upserts into the uni-specific partition via PgBouncer.
    """
    # Simulated API data fetch for University uni_id
    dummy_records = [
        {"course_id": 1, "attendees": 450, "graduates": 120},
        {"course_id": 2, "attendees": 200, "graduates": 85},
        {"course_id": 3, "attendees": 310, "graduates": 95}
    ]

    with pool.connection() as conn:
        with conn.cursor() as cur:
            processed = 0
            for rec in dummy_records:
                cur.execute(
                    "SELECT sp_upsert_yearly_metrics(%s, %s, %s, %s, %s);",
                    (uni_id, rec["course_id"], target_year, rec["attendees"], rec["graduates"])
                )
                processed += 1

            # Log successful execution in audit table
            cur.execute(
                """
                INSERT INTO ingestion_audit_log (uni_id, academic_year, records_processed, status)
                VALUES (%s, %s, %s, %s);
                """,
                (uni_id, target_year, processed, "SUCCESS")
            )
        conn.commit()
    return f"University {uni_id} loaded successfully ({processed} records)"

def run_pipeline(uni_ids: list[int], target_year: int, max_threads: int = 8, db_uri: str = DB_URI):
    logging.info(f"Starting parallel pipeline for Year {target_year} across {len(uni_ids)} universities using {max_threads} threads.")

    pool = get_pool(db_uri)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = {
                executor.submit(worker_load_university, pool, uni, target_year): uni
                for uni in uni_ids
            }
            for future in concurrent.futures.as_completed(futures):
                uni = futures[future]
                try:
                    result = future.result()
                    logging.info(result)
                except Exception as e:
                    logging.error(f"Failed loading University {uni}: {e}")
    finally:
        pool.close()

if __name__ == "__main__":
    universities = [101, 102, 103, 104, 105, 106, 107, 108]
    run_pipeline(uni_ids=universities, target_year=2024, max_threads=4)
