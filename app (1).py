"""
app.py  —  Mentorship Matching System · Streamlit Frontend
-----------------------------------------------------------
Tabs:
  1. Connect     — configure and test DB connection
  2. Upload Data — upload mentor / mentee CSVs and insert into DB
  3. Run Matching — trigger the keyword-matching algorithm
  4. View Results — browse all tables in the database
"""

import io
import csv
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd

# ------------------------------------------------------------------
# Page config
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Mentorship Matching System",
    page_icon="🎓",
    layout="wide",
)

# ------------------------------------------------------------------
# Session state defaults
# ------------------------------------------------------------------
if "connected" not in st.session_state:
    st.session_state.connected = False
if "conn_params" not in st.session_state:
    st.session_state.conn_params = {}


# ------------------------------------------------------------------
# DB helpers
# ------------------------------------------------------------------

def get_conn():
    p = st.session_state.conn_params
    return psycopg2.connect(**p)


def run_query(sql, params=None):
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    conn.close()
    return pd.DataFrame(rows)


def run_execute(sql, params=None):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected


# ------------------------------------------------------------------
# Insert helpers
# ------------------------------------------------------------------

def insert_mentors_df(df: pd.DataFrame):
    conn = get_conn()
    inserted = 0
    errors = []
    with conn.cursor() as cur:
        for _, r in df.iterrows():
            try:
                cur.execute("""
                    INSERT INTO Person (person_id, first_name, middle_name, last_name, email, role)
                    VALUES (%s,%s,%s,%s,%s,'mentor')
                    ON CONFLICT (person_id) DO NOTHING
                """, (
                    r["person_id"], r["first_name"],
                    r.get("middle_name") or None,
                    r["last_name"], r["email"],
                ))
                cur.execute("""
                    INSERT INTO Mentor (mentor_id)
                    VALUES (%s)
                    ON CONFLICT (mentor_id) DO NOTHING
                """, (r["person_id"],))
                for kw in [k.strip() for k in str(r["keywords"]).split(";") if k.strip()]:
                    cur.execute("""
                        INSERT INTO Mentor_Skill (mentor_id, keyword)
                        VALUES (%s,%s) ON CONFLICT DO NOTHING
                    """, (r["person_id"], kw))
                inserted += 1
            except Exception as e:
                errors.append(f"Row {r['person_id']}: {e}")
                conn.rollback()
    conn.commit()
    conn.close()
    return inserted, errors


def insert_mentees_df(df: pd.DataFrame):
    conn = get_conn()
    inserted = 0
    errors = []
    with conn.cursor() as cur:
        for _, r in df.iterrows():
            try:
                cur.execute("""
                    INSERT INTO Person (person_id, first_name, middle_name, last_name, email, role)
                    VALUES (%s,%s,%s,%s,%s,'mentee')
                    ON CONFLICT (person_id) DO NOTHING
                """, (
                    r["person_id"], r["first_name"],
                    r.get("middle_name") or None,
                    r["last_name"], r["email"],
                ))
                cur.execute("""
                    INSERT INTO Mentee (mentee_id)
                    VALUES (%s) ON CONFLICT DO NOTHING
                """, (r["person_id"],))
                for kw in [k.strip() for k in str(r["keywords"]).split(";") if k.strip()]:
                    cur.execute("""
                        INSERT INTO Mentee_Interest (mentee_id, keyword)
                        VALUES (%s,%s) ON CONFLICT DO NOTHING
                    """, (r["person_id"], kw))
                inserted += 1
            except Exception as e:
                errors.append(f"Row {r['person_id']}: {e}")
                conn.rollback()
    conn.commit()
    conn.close()
    return inserted, errors


MATCH_SQL = """
INSERT INTO Match (mentee_id, mentor_id)
SELECT DISTINCT ON (ranked.mentee_id)
    ranked.mentee_id,
    ranked.mentor_id
FROM (
    SELECT
        mi.mentee_id,
        ms.mentor_id,
        COUNT(*) AS keyword_overlap
    FROM Mentee_Interest mi
    JOIN Mentor_Skill    ms ON LOWER(ms.keyword) = LOWER(mi.keyword)
    JOIN Mentor          mr ON mr.mentor_id      = ms.mentor_id
    WHERE mi.mentee_id NOT IN (SELECT mentee_id FROM Match)
    GROUP BY mi.mentee_id, ms.mentor_id
) ranked
ORDER BY ranked.mentee_id, ranked.keyword_overlap DESC
ON CONFLICT (mentee_id) DO NOTHING
"""


# ==================================================================
# SIDEBAR — connection
# ==================================================================
with st.sidebar:
    st.markdown("## 🔌 Database Connection")
    dbname   = st.text_input("Database",  value="mentorship_db")
    user     = st.text_input("User",      value="postgres")
    password = st.text_input("Password",  type="password")
    host     = st.text_input("Host",      value="localhost")
    port     = st.number_input("Port",    value=5432, step=1)

    if st.button("Connect", use_container_width=True):
        try:
            params = dict(dbname=dbname, user=user,
                          password=password, host=host, port=int(port))
            test = psycopg2.connect(**params)
            test.close()
            st.session_state.connected = True
            st.session_state.conn_params = params
            st.success("Connected!")
        except Exception as e:
            st.session_state.connected = False
            st.error(f"Failed: {e}")

    if st.session_state.connected:
        st.markdown("---")
        st.success("● Connected")
    else:
        st.warning("Not connected")


# ==================================================================
# MAIN AREA
# ==================================================================
st.title("🎓 Mentorship Matching System")

if not st.session_state.connected:
    st.info("Configure your database connection in the sidebar to get started.")
    st.stop()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📤 Upload Data",
    "⚡ Run Matching",
    "📊 View Results",
    "🗄️ Browse Tables",
    "⭐ Submit Feedback",
])


# ------------------------------------------------------------------
# TAB 1 — Upload Data
# ------------------------------------------------------------------
with tab1:
    st.subheader("Upload Mentor CSV")
    mentor_file = st.file_uploader(
        "mentors.csv  (columns: person_id, first_name, middle_name, last_name, email, keywords)",
        type="csv", key="mentor_upload"
    )
    if mentor_file:
        mentor_df = pd.read_csv(mentor_file)
        st.dataframe(mentor_df, use_container_width=True)
        if st.button("Insert Mentors into DB"):
            n, errs = insert_mentors_df(mentor_df)
            if errs:
                for e in errs:
                    st.error(e)
            st.success(f"Inserted / skipped {n} mentor(s).")

    st.divider()

    st.subheader("Upload Mentee CSV")
    mentee_file = st.file_uploader(
        "mentees.csv  (columns: person_id, first_name, middle_name, last_name, email, keywords)",
        type="csv", key="mentee_upload"
    )
    if mentee_file:
        mentee_df = pd.read_csv(mentee_file)
        st.dataframe(mentee_df, use_container_width=True)
        if st.button("Insert Mentees into DB"):
            n, errs = insert_mentees_df(mentee_df)
            if errs:
                for e in errs:
                    st.error(e)
            st.success(f"Inserted / skipped {n} mentee(s).")


# ------------------------------------------------------------------
# TAB 2 — Run Matching
# ------------------------------------------------------------------
with tab2:
    st.subheader("Keyword Matching Algorithm")
    st.markdown("""
The algorithm finds the **best mentor** for each unmatched mentee by:
1. Joining `Mentee_Interest` ↔ `Mentor_Skill` on keyword (case-insensitive)
2. Ranking candidates by **keyword overlap** (most shared keywords first)
3. Breaking ties by **mentor skill level** (higher is better)
4. Inserting one row per mentee into the `Match` table
""")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Unmatched mentees")
        unmatched = run_query("""
            SELECT ee.mentee_id,
                   p.first_name || ' ' || p.last_name AS name,
                   STRING_AGG(mi.keyword, ', ')        AS interests
            FROM Mentee ee
            JOIN Person p             ON p.person_id = ee.mentee_id
            JOIN Mentee_Interest mi   ON mi.mentee_id = ee.mentee_id
            WHERE ee.mentee_id NOT IN (SELECT mentee_id FROM Match)
            GROUP BY ee.mentee_id, p.first_name, p.last_name
        """)
        if unmatched.empty:
            st.info("All mentees are already matched.")
        else:
            st.dataframe(unmatched, use_container_width=True)

    with col2:
        st.markdown("#### Compatible pairs (preview)")
        pairs = run_query("""
            SELECT mi.mentee_id,
                   p_ee.first_name || ' ' || p_ee.last_name  AS mentee,
                   mi.keyword                                 AS shared_keyword,
                   ms.mentor_id,
                   p_mr.first_name || ' ' || p_mr.last_name  AS mentor
            FROM Mentee_Interest mi
            JOIN Person          p_ee ON p_ee.person_id = mi.mentee_id
            JOIN Mentor_Skill    ms   ON LOWER(ms.keyword) = LOWER(mi.keyword)
            JOIN Mentor          mr   ON mr.mentor_id     = ms.mentor_id
            JOIN Person          p_mr ON p_mr.person_id   = mr.mentor_id
            WHERE mi.mentee_id NOT IN (SELECT mentee_id FROM Match)
            ORDER BY mi.mentee_id
        """)
        if pairs.empty:
            st.info("No compatible pairs found (or all matched).")
        else:
            st.dataframe(pairs, use_container_width=True)

    st.divider()
    if st.button("▶ Run Matching Now", type="primary", use_container_width=True):
        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(MATCH_SQL)
                n = cur.rowcount
            conn.commit()
            conn.close()
            st.success(f"✅ Matching complete — {n} new match(es) created.")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


# ------------------------------------------------------------------
# TAB 3 — View Results
# ------------------------------------------------------------------
with tab3:
    st.subheader("Match Results")
    results = run_query("""
        SELECT
            m.match_id,
            p_ee.first_name || ' ' || p_ee.last_name   AS mentee,
            STRING_AGG(DISTINCT mi.keyword, ', ')       AS mentee_interests,
            p_mr.first_name || ' ' || p_mr.last_name   AS mentor,
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
    """)

    if results.empty:
        st.info("No matches yet. Go to the 'Run Matching' tab.")
    else:
        total = len(results)
        st.metric("Total Matches", total)

        st.dataframe(results, use_container_width=True, hide_index=True)

        csv_out = results.to_csv(index=False).encode()
        st.download_button("⬇ Download results as CSV", csv_out,
                           file_name="match_results.csv", mime="text/csv")


# ------------------------------------------------------------------
# TAB 4 — Browse Tables
# ------------------------------------------------------------------
with tab4:
    st.subheader("Browse Database Tables")
    table = st.selectbox("Select table", [
        "person", "mentor", "mentee",
        "mentor_skill", "mentee_interest", "match", "feedback"
    ])
    try:
        df = run_query(f'SELECT * FROM {table} ORDER BY 1')
        st.dataframe(df, use_container_width=True)
        st.caption(f"{len(df)} row(s)")
    except Exception as e:
        st.error(f"Could not load table: {e}")


# ------------------------------------------------------------------
# TAB 5 — Submit Feedback
# ------------------------------------------------------------------
with tab5:
    st.subheader("Submit Feedback")
    st.markdown("Rate your mentorship experience. Both mentor and mentee ratings are required.")

    matches = run_query("""
        SELECT
            m.match_id,
            p_ee.first_name || ' ' || p_ee.last_name AS mentee_name,
            p_mr.first_name || ' ' || p_mr.last_name AS mentor_name
        FROM match m
        JOIN person p_ee ON p_ee.person_id = m.mentee_id
        JOIN person p_mr ON p_mr.person_id = m.mentor_id
        ORDER BY m.match_id
    """)

    if matches.empty:
        st.info("No matches yet. Run matching first.")
    else:
        match_options = {
            f"Match {row.match_id}: {row.mentee_name} ↔ {row.mentor_name}": row.match_id
            for row in matches.itertuples()
        }
        selected_label = st.selectbox("Select a match", list(match_options.keys()))
        selected_match_id = match_options[selected_label]

        existing = run_query(f"SELECT * FROM feedback WHERE match_id = {selected_match_id}")
        if not existing.empty:
            st.warning("Feedback already submitted for this match.")
            st.dataframe(existing, use_container_width=True, hide_index=True)
        else:
            col1, col2 = st.columns(2)
            with col1:
                mentor_rating = st.slider("Mentee's rating of the mentor", 1, 5, 3)
                st.caption("How helpful was the mentor?")
            with col2:
                mentee_rating = st.slider("Mentor's rating of the mentee", 1, 5, 3)
                st.caption("How engaged was the mentee?")

            if st.button("Submit Feedback", type="primary", use_container_width=True):
                try:
                    conn = get_conn()
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO feedback (match_id, mentor_rating, mentee_rating)
                            VALUES (%s, %s, %s)
                        """, (selected_match_id, mentor_rating, mentee_rating))
                    conn.commit()
                    conn.close()
                    st.success(f"Feedback submitted for Match {selected_match_id}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()
    st.markdown("#### All submitted feedback")
    all_feedback = run_query("""
        SELECT
            f.match_id,
            p_ee.first_name || ' ' || p_ee.last_name AS mentee,
            p_mr.first_name || ' ' || p_mr.last_name AS mentor,
            f.mentor_rating,
            f.mentee_rating
        FROM feedback f
        JOIN match   m    ON m.match_id    = f.match_id
        JOIN person  p_ee ON p_ee.person_id = m.mentee_id
        JOIN person  p_mr ON p_mr.person_id = m.mentor_id
        ORDER BY f.match_id
    """)
    if all_feedback.empty:
        st.info("No feedback submitted yet.")
    else:
        st.dataframe(all_feedback, use_container_width=True, hide_index=True)