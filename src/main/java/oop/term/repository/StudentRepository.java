package oop.term.repository;

import oop.term.model.Student;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.UUID;

public interface StudentRepository extends JpaRepository<Student, Integer> {
    @Query(nativeQuery = true, value = "SELECT * FROM student WHERE address = ?1")
    Student findByAddress(String address);
}
