package oop.term.model;

import javax.persistence.*;
import java.util.List;


@Entity
//@EqualsAndHashCode(callSuper = true)
public class Student extends AbstractUser {

    @OneToMany(fetch = FetchType.EAGER)
    @JoinColumn(name = "students_id")
    private List<Grade> gradeList;

    @Transient
    private int avgGrade;

    public Student() {
    }

    public Student(String fullName, String address, String phoneNumber, Course course, List<Grade> gradeList) {
        super(fullName, address, phoneNumber, course);
        this.gradeList = gradeList;
    }

    public List<Grade> getGradeList() {
        return gradeList;
    }

    public void setGradeList(List<Grade> gradeList) {
        this.gradeList = gradeList;
    }

    public int getAvgGrade() {
        return avgGrade;
    }

    public void setAvgGrade(int avgGrade) {
        this.avgGrade = avgGrade;
    }
}
