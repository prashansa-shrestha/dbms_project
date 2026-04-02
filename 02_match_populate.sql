-- ============================================================
-- 02_match_populate.sql
-- Step 1: VIEW all compatible (mentee, mentor) pairs
-- Step 2: INSERT best match per mentee into Match table
-- Best match = most keyword overlap
-- Run AFTER 01_insert_data.sql
-- ============================================================

-- ------------------------------------------------------------
-- STEP 1: Search — see all compatible pairs before committing
-- ------------------------------------------------------------
SELECT
    mi.mentee_id,
    p_ee.first_name || ' ' || p_ee.last_name       AS mentee_name,
    mi.keyword                                      AS shared_keyword,
    ms.mentor_id,
    p_mr.first_name || ' ' || p_mr.last_name       AS mentor_name
FROM Mentee_Interest mi
JOIN Person          p_ee ON p_ee.person_id = mi.mentee_id
JOIN Mentor_Skill    ms   ON LOWER(ms.keyword) = LOWER(mi.keyword)
JOIN Mentor          mr   ON mr.mentor_id     = ms.mentor_id
JOIN Person          p_mr ON p_mr.person_id   = mr.mentor_id
ORDER BY mi.mentee_id;


-- ------------------------------------------------------------
-- STEP 2: Populate — insert best mentor per mentee
-- Ranked by most keyword overlap
-- ------------------------------------------------------------
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
    WHERE mi.mentee_id NOT IN (SELECT mentee_id FROM Match)
    GROUP BY mi.mentee_id, ms.mentor_id
) ranked
ORDER BY ranked.mentee_id, ranked.keyword_overlap DESC
ON CONFLICT (mentee_id) DO NOTHING;


-- ------------------------------------------------------------
-- STEP 3: Verify — view the final match results
-- ------------------------------------------------------------
SELECT
    m.match_id,
    p_ee.first_name || ' ' || p_ee.last_name   AS mentee_name,
    p_mr.first_name || ' ' || p_mr.last_name   AS mentor_name,
    STRING_AGG(DISTINCT mi.keyword, ', ')       AS mentee_interests,
    STRING_AGG(DISTINCT ms.keyword, ', ')       AS mentor_skills
FROM Match m
JOIN Mentee          ee   ON ee.mentee_id     = m.mentee_id
JOIN Person          p_ee ON p_ee.person_id   = m.mentee_id
JOIN Mentor          mr   ON mr.mentor_id     = m.mentor_id
JOIN Person          p_mr ON p_mr.person_id   = m.mentor_id
JOIN Mentee_Interest mi   ON mi.mentee_id     = m.mentee_id
JOIN Mentor_Skill    ms   ON ms.mentor_id     = m.mentor_id
GROUP BY m.match_id, p_ee.first_name, p_ee.last_name,
         p_mr.first_name, p_mr.last_name
ORDER BY m.match_id;
