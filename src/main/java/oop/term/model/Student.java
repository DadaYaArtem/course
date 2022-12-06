package oop.term.model;

import lombok.EqualsAndHashCode;

import javax.persistence.Entity;
import javax.persistence.FetchType;
import javax.persistence.JoinColumn;
import javax.persistence.OneToMany;
import java.util.List;


@Entity
//@EqualsAndHashCode(callSuper = true)
public class Student extends AbstractUser {

    @OneToMany(fetch = FetchType.EAGER)
    @JoinColumn(name = "students_id")
    private List<Grade> gradeList;

    public Student() {
    }

    public Student(String fullName, String address, String phoneNumber, Course course, List<Grade> gradeList) {
        super(fullName, address, phoneNumber, course);
        this.gradeList = gradeList;
    }
}
