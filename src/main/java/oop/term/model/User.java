package oop.term.model;

import lombok.Data;

import javax.persistence.*;
import java.util.UUID;

@MappedSuperclass
@Data
public abstract class User {
    @Id
    @GeneratedValue
    private UUID id;

    @Column(name = "full_name")
    private String fullName;

    private String address;

    @Column(name = "phone_number")
    private String phoneNumber;

    @Enumerated(EnumType.STRING)
    private Course course;

    public User() {
    }

    public User(String fullName, String address, String phoneNumber, Course course) {
        this.fullName = fullName;
        this.address = address;
        this.phoneNumber = phoneNumber;
        this.course = course;
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public String getFullName() {
        return fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = fullName;
    }

    public String getAddress() {
        return address;
    }

    public void setAddress(String address) {
        this.address = address;
    }

    public String getPhoneNumber() {
        return phoneNumber;
    }

    public void setPhoneNumber(String phoneNumber) {
        this.phoneNumber = phoneNumber;
    }

    public Course getCourse() {
        return course;
    }

    public void setCourse(Course course) {
        this.course = course;
    }
}
