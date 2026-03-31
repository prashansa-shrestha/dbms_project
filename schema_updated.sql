-- ============================================================
-- Mentorship Matching System — Schema
-- Matches dbdiagram.io structure exactly
-- ============================================================

CREATE TABLE Person (
    person_id   VARCHAR PRIMARY KEY,
    first_name  VARCHAR NOT NULL,
    middle_name VARCHAR,
    last_name   VARCHAR NOT NULL,
    email       VARCHAR NOT NULL UNIQUE,
    role        VARCHAR NOT NULL CHECK (role IN ('mentor', 'mentee'))
);

CREATE TABLE Mentor (
    mentor_id   VARCHAR PRIMARY KEY REFERENCES Person(person_id)
);

CREATE TABLE Mentee (
    mentee_id   VARCHAR PRIMARY KEY REFERENCES Person(person_id)
);

CREATE TABLE Mentor_Skill (
    mentor_id   VARCHAR NOT NULL REFERENCES Mentor(mentor_id) ON DELETE CASCADE,
    keyword     VARCHAR NOT NULL,
    PRIMARY KEY (mentor_id, keyword)
);

CREATE TABLE Mentee_Interest (
    mentee_id   VARCHAR NOT NULL REFERENCES Mentee(mentee_id) ON DELETE CASCADE,
    keyword     VARCHAR NOT NULL,
    PRIMARY KEY (mentee_id, keyword)
);

CREATE TABLE Match (
    match_id    SERIAL PRIMARY KEY,
    mentee_id   VARCHAR UNIQUE REFERENCES Mentee(mentee_id),
    mentor_id   VARCHAR REFERENCES Mentor(mentor_id)
);

CREATE TABLE Feedback (
    match_id        INTEGER PRIMARY KEY REFERENCES Match(match_id) ON DELETE CASCADE,
    mentor_rating   INTEGER CHECK (mentor_rating BETWEEN 1 AND 5),
    mentee_rating   INTEGER CHECK (mentee_rating BETWEEN 1 AND 5)
);

-- ============================================================
-- Triggers: enforce disjoint ISA (role must match subtype)
-- ============================================================

CREATE OR REPLACE FUNCTION check_mentor_role() RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT role FROM Person WHERE person_id = NEW.mentor_id) <> 'mentor' THEN
        RAISE EXCEPTION 'Person % does not have role=mentor', NEW.mentor_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_mentor_role
    BEFORE INSERT OR UPDATE ON Mentor
    FOR EACH ROW EXECUTE FUNCTION check_mentor_role();

CREATE OR REPLACE FUNCTION check_mentee_role() RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT role FROM Person WHERE person_id = NEW.mentee_id) <> 'mentee' THEN
        RAISE EXCEPTION 'Person % does not have role=mentee', NEW.mentee_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_mentee_role
    BEFORE INSERT OR UPDATE ON Mentee
    FOR EACH ROW EXECUTE FUNCTION check_mentee_role();
