CREATE TABLE mentor(
     id SERIAL,
     address varchar(255),
     course varchar(255),
     full_name varchar(255),
     phone_number varchar(255),
     cabinet_number int4,
     subject varchar(100),
     experience int4,
     primary key (id)
);