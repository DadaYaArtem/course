package oop.term.model;

import javax.persistence.*;

@Entity
public class Mentor extends AbstractUser{
    private int experience; // in months
    @Column(name = "cabinet_number")
    private int cabinetNumber;
    @Enumerated(EnumType.STRING)
    private Subject subject;

    public Mentor() {
    }

    public Mentor(String fullName, String address, String phoneNumber, Course course, int experience, int cabinetNumber, Subject subject) {
        super(fullName, address, phoneNumber, course);
        this.experience = experience;
        this.cabinetNumber = cabinetNumber;
        this.subject = subject;
    }

    public int getExperience() {
        return experience;
    }

    public void setExperience(int experience) {
        this.experience = experience;
    }

    public int getCabinetNumber() {
        return cabinetNumber;
    }

    public void setCabinetNumber(int cabinetNumber) {
        this.cabinetNumber = cabinetNumber;
    }

    public Subject getSubject() {
        return subject;
    }

    public void setSubject(Subject subject) {
        this.subject = subject;
    }
}
