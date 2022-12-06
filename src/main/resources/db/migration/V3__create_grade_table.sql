CREATE TABLE grade
(
    id UUID DEFAULT gen_random_uuid(),
    subject VARCHAR(100),
    grade int4,
    students_id UUID,
    PRIMARY KEY (id),
    CONSTRAINT fk_users FOREIGN KEY (students_id) REFERENCES student (id)
);