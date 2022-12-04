package oop.term.users;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import oop.term.users.students.Course;

import javax.persistence.*;

public abstract class User {
    private Long id;

    private String email;

    private String password;

    private String phone_number;

    private Course course;

    private String address;
}
