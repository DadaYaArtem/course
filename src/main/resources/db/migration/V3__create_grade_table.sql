CREATE TABLE grade
(
    id SERIAL,
    subject VARCHAR(100),
    grade int4,
    students_id int4,
    PRIMARY KEY (id),
    CONSTRAINT fk_users FOREIGN KEY (students_id) REFERENCES student (id)
);