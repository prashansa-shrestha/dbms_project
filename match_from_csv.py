"""
match_from_csv.py
-----------------
Reads mentors.csv and mentees.csv, inserts all rows into the
database, then runs the keyword-matching algorithm to populate
the Match table.

Usage:
    python match_from_csv.py \
        --mentors mentors.csv \
        --mentees mentees.csv \
        --dbname mentorship_db \
        --user postgres \
        --password yourpassword \
        --host localhost \
        --port 5432
"""

import argparse
import csv
import os
from pathlib import Path
import sys
import psycopg2
from psycopg2.extras import execute_values


# ------------------------------------------------------------------
# Env loader (reads .env if present)
# ------------------------------------------------------------------
def load_env(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key and key not in os.environ:
            os.environ[key.strip()] = val.strip()


load_env()


# ------------------------------------------------------------------
# DB helpers
# ------------------------------------------------------------------

def get_conn(args):
    return psycopg2.connect(
        dbname=args.dbname,
        user=args.user,
        password=args.password,
        host=args.host,
        port=args.port,
    )


# ------------------------------------------------------------------
# Insert mentors from CSV
# ------------------------------------------------------------------

def insert_mentors(conn, filepath):
    print(f"[mentors] reading {filepath} ...")
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    with conn.cursor() as cur:
        for r in rows:
            # Person
            cur.execute("""
                INSERT INTO Person (person_id, first_name, middle_name, last_name, email, role)
                VALUES (%s, %s, %s, %s, %s, 'mentor')
                ON CONFLICT (person_id) DO NOTHING
            """, (
                r["person_id"],
                r["first_name"],
                r["middle_name"] if r["middle_name"] else None,
                r["last_name"],
                r["email"],
            ))

            # Mentor
            cur.execute("""
                INSERT INTO Mentor (mentor_id)
                VALUES (%s)
                ON CONFLICT (mentor_id) DO NOTHING
            """, (r["person_id"],))

            # Mentor_Skill (semicolon-separated keywords)
            keywords = [k.strip() for k in r["keywords"].split(";") if k.strip()]
            for kw in keywords:
                cur.execute("""
                    INSERT INTO Mentor_Skill (mentor_id, keyword)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (r["person_id"], kw))

    conn.commit()
    print(f"[mentors] inserted {len(rows)} mentor(s).")


# ------------------------------------------------------------------
# Insert mentees from CSV
# ------------------------------------------------------------------

def insert_mentees(conn, filepath):
    print(f"[mentees] reading {filepath} ...")
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    with conn.cursor() as cur:
        for r in rows:
            # Person
            cur.execute("""
                INSERT INTO Person (person_id, first_name, middle_name, last_name, email, role)
                VALUES (%s, %s, %s, %s, %s, 'mentee')
                ON CONFLICT (person_id) DO NOTHING
            """, (
                r["person_id"],
                r["first_name"],
                r["middle_name"] if r["middle_name"] else None,
                r["last_name"],
                r["email"],
            ))

            # Mentee
            cur.execute("""
                INSERT INTO Mentee (mentee_id)
                VALUES (%s)
                ON CONFLICT (mentee_id) DO NOTHING
            """, (r["person_id"],))

            # Mentee_Interest
            keywords = [k.strip() for k in r["keywords"].split(";") if k.strip()]
            for kw in keywords:
                cur.execute("""
                    INSERT INTO Mentee_Interest (mentee_id, keyword)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (r["person_id"], kw))

    conn.commit()
    print(f"[mentees] inserted {len(rows)} mentee(s).")


# ------------------------------------------------------------------
# Populate Match table (best mentor per mentee by overlap)
# ------------------------------------------------------------------

MATCH_SQL = """
INSERT INTO Match (mentee_id, mentor_id)
SELECT DISTINCT ON (ranked.mentee_id)
    ranked.mentee_id,
    ranked.mentor_id
FROM (
    SELECT
        mi.mentee_id,
        ms.mentor_id,
        COUNT(*)    AS keyword_overlap
    FROM Mentee_Interest mi
    JOIN Mentor_Skill    ms ON LOWER(ms.keyword) = LOWER(mi.keyword)
    JOIN Mentor          mr ON mr.mentor_id      = ms.mentor_id
    WHERE mi.mentee_id NOT IN (SELECT mentee_id FROM Match)
    GROUP BY mi.mentee_id, ms.mentor_id
) ranked
ORDER BY ranked.mentee_id, ranked.keyword_overlap DESC
ON CONFLICT (mentee_id) DO NOTHING
"""

def populate_matches(conn):
    print("[matches] running keyword-matching algorithm ...")
    with conn.cursor() as cur:
        cur.execute(MATCH_SQL)
        count = cur.rowcount
    conn.commit()
    print(f"[matches] inserted {count} new match(es).")


# ------------------------------------------------------------------
# Print results
# ------------------------------------------------------------------

RESULTS_SQL = """
SELECT
    m.match_id,
    p_ee.first_name || ' ' || p_ee.last_name   AS mentee,
    p_mr.first_name || ' ' || p_mr.last_name   AS mentor,
    STRING_AGG(DISTINCT mi.keyword, ', ')       AS mentee_interests,
    STRING_AGG(DISTINCT ms.keyword, ', ')       AS mentor_skills
FROM Match m
JOIN Mentee          ee   ON ee.mentee_id   = m.mentee_id
JOIN Person          p_ee ON p_ee.person_id = m.mentee_id
JOIN Mentor          mr   ON mr.mentor_id   = m.mentor_id
JOIN Person          p_mr ON p_mr.person_id = m.mentor_id
JOIN Mentee_Interest mi   ON mi.mentee_id   = m.mentee_id
JOIN Mentor_Skill    ms   ON ms.mentor_id   = m.mentor_id
GROUP BY m.match_id, p_ee.first_name, p_ee.last_name,
         p_mr.first_name, p_mr.last_name
ORDER BY m.match_id
"""

def print_results(conn):
    with conn.cursor() as cur:
        cur.execute(RESULTS_SQL)
        rows = cur.fetchall()

    print("\n" + "=" * 70)
    print(f"{'ID':<5} {'Mentee':<20} {'Mentor':<20} {'Shared Keywords'}")
    print("=" * 70)
    for row in rows:
        match_id, mentee, mentor, interests, skills = row
        overlap = set(interests.split(", ")) & set(skills.split(", "))
        print(f"{match_id:<5} {mentee:<20} {mentor:<20} {', '.join(overlap)}")
    print("=" * 70)
    print(f"Total matches: {len(rows)}\n")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Load CSVs and populate Match table")
    parser.add_argument("--mentors",  default="mentors.csv")
    parser.add_argument("--mentees",  default="mentees.csv")
    parser.add_argument("--dbname",   default=os.getenv("DB_NAME", "mentorship_db"))
    parser.add_argument("--user",     default=os.getenv("DB_USER", "postgres"))
    parser.add_argument("--password", default=os.getenv("DB_PASSWORD", ""))
    parser.add_argument("--host",     default=os.getenv("DB_HOST", "localhost"))
    parser.add_argument("--port",     type=int, default=int(os.getenv("DB_PORT", "5432")))
    args = parser.parse_args()

    try:
        conn = get_conn(args)
        print("[db] connected successfully.")
    except Exception as e:
        print(f"[db] connection failed: {e}")
        sys.exit(1)

    insert_mentors(conn, args.mentors)
    insert_mentees(conn, args.mentees)
    populate_matches(conn)
    print_results(conn)
    conn.close()


if __name__ == "__main__":
    main()