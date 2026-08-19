import logging
import os
import psycopg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgrespassword@localhost:6432/edu_metrics")
PARTITIONED_TABLES = ["yearly_metrics"]

def get_all_university_ids(conn: psycopg.Connection) -> list[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT uni_id FROM university ORDER BY uni_id ASC;")
        return [row[0] for row in cur.fetchall()]

def get_existing_partitions(conn: psycopg.Connection, parent_table: str) -> set[str]:
    query = """
        SELECT c.relname
        FROM pg_class c
        JOIN pg_inherits i ON c.oid = i.inhrelid
        JOIN pg_class p ON p.oid = i.inhparent
        WHERE p.relname = %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (parent_table,))
        return {row[0] for row in cur.fetchall()}

def create_missing_partitions(db_uri: str = DB_URI):
    try:
        with psycopg.connect(db_uri, autocommit=True) as conn:
            uni_ids = get_all_university_ids(conn)
            logging.info(f"Found {len(uni_ids)} total universities registered.")
            for parent_table in PARTITIONED_TABLES:
                existing_partitions = get_existing_partitions(conn, parent_table)
                created_count = 0
                for uni_id in uni_ids:
                    partition_name = f"{parent_table}_uni_{uni_id}"
                    if partition_name not in existing_partitions:
                        ddl_sql = f"""
                            CREATE TABLE IF NOT EXISTS {partition_name}
                            PARTITION OF {parent_table}
                            FOR VALUES IN ({uni_id});
                        """
                        with conn.cursor() as cur:
                            cur.execute(ddl_sql)
                        logging.info(f"Created partition: {partition_name}")
                        created_count += 1
                logging.info(f"Table '{parent_table}': {created_count} new partitions created.")
    except Exception as e:
        logging.error(f"Error during partition maintenance: {e}")
        raise

if __name__ == "__main__":
    create_missing_partitions()
