-- ============================================================
-- 01_insert_data.sql
-- Manual demo data: 6 mentors, 6 mentees
-- Some entries have 2 rows in Mentor_Skill / Mentee_Interest
-- Run AFTER schema_updated.sql
-- ============================================================

INSERT INTO Person (person_id, first_name, middle_name, last_name, email, role) VALUES
    ('mentor_1', 'Asha',    NULL,    'Sharma',    'asha@pcampus.edu.np',    'mentor'),
    ('mentor_2', 'Bikram',  NULL,    'Thapa',     'bikram@pcampus.edu.np',  'mentor'),
    ('mentor_3', 'Chitra',  NULL,    'Rai',       'chitra@pcampus.edu.np',  'mentor'),
    ('mentor_4', 'Deepak',  'Raj',   'Joshi',     'deepak@pcampus.edu.np',  'mentor'),
    ('mentor_5', 'Elina',   NULL,    'Magar',     'elina@pcampus.edu.np',   'mentor'),
    ('mentor_6', 'Farhan',  'Ali',   'Ansari',    'farhan@pcampus.edu.np',  'mentor'),
    ('mentee_1', 'Gita',    NULL,    'Tamang',    'gita@pcampus.edu.np',    'mentee'),
    ('mentee_2', 'Hari',    NULL,    'Khadka',    'hari@pcampus.edu.np',    'mentee'),
    ('mentee_3', 'Ishaan',  NULL,    'Pradhan',   'ishaan@pcampus.edu.np',  'mentee'),
    ('mentee_4', 'Jaya',    'Devi',  'Shrestha',  'jaya@pcampus.edu.np',   'mentee'),
    ('mentee_5', 'Kiran',   NULL,    'Basnet',    'kiran@pcampus.edu.np',   'mentee'),
    ('mentee_6', 'Laxmi',   NULL,    'Gurung',    'laxmi@pcampus.edu.np',   'mentee');

INSERT INTO Mentor (mentor_id) VALUES
    ('mentor_1'),
    ('mentor_2'),
    ('mentor_3'),
    ('mentor_4'),
    ('mentor_5'),
    ('mentor_6');

INSERT INTO Mentor_Skill (mentor_id, keyword) VALUES
    ('mentor_1', 'Machine Learning'),
    ('mentor_1', 'Data Science'),
    ('mentor_2', 'Web Development'),
    ('mentor_3', 'Machine Learning'),
    ('mentor_3', 'Python'),
    ('mentor_4', 'Cloud Computing'),
    ('mentor_5', 'Cybersecurity'),
    ('mentor_5', 'Cloud Computing'),
    ('mentor_6', 'Data Science');

INSERT INTO Mentee (mentee_id) VALUES
    ('mentee_1'),
    ('mentee_2'),
    ('mentee_3'),
    ('mentee_4'),
    ('mentee_5'),
    ('mentee_6');

INSERT INTO Mentee_Interest (mentee_id, keyword) VALUES
    ('mentee_1', 'Machine Learning'),
    ('mentee_1', 'Data Science'),
    ('mentee_2', 'Web Development'),
    ('mentee_3', 'Machine Learning'),
    ('mentee_3', 'Python'),
    ('mentee_4', 'Cloud Computing'),
    ('mentee_5', 'Cybersecurity'),
    ('mentee_5', 'Cloud Computing'),
    ('mentee_6', 'Data Science');
