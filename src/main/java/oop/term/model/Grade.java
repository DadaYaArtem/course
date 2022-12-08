package oop.term.model;

import lombok.Data;

import javax.persistence.*;
import java.util.UUID;

@Data
@Entity
@Table(name = "grade")
public class Grade {
    @Id
    @Column(name = "id")
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer studentId;
    @Enumerated(EnumType.STRING)
    private Subject subject;
    private int grade; // 0-bad, 90-ok, but can be better, 100- excellent

    public Grade() {
    }

    public Grade(Subject subject, int grade) {
        this.subject = subject;
        this.grade = grade;
    }

    public Integer getStudentId() {
        return studentId;
    }

    public void setStudentId(Integer studentId) {
        this.studentId = studentId;
    }

    public enum Subject{
        MATH,
        PROGRAMMING,
        ENGLISH
    }
}
