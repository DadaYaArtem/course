package oop.term.model;

import lombok.Data;
import lombok.EqualsAndHashCode;

import javax.persistence.Entity;


@Entity
@EqualsAndHashCode(callSuper = true)
public class Student extends User {

    public Student() {
    }

    public Student(String fullName, String address, String phoneNumber, Course course) {
        super(fullName, address, phoneNumber, course);
    }


}
