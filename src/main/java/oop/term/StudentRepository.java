package oop.term;

import oop.term.model.Student;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface StudentRepository extends JpaRepository<Student, Long> {
    @Query(nativeQuery = true, value = "SELECT * FROM student WHERE address = ?1")
    Student findByAddress(String email);
}
