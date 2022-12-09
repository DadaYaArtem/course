package oop.term.repository;

import oop.term.model.Grade;
import oop.term.model.Student;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;

public interface GradeRepository extends JpaRepository<Grade, Integer> {
    @Query(nativeQuery = true, value = "SELECT * FROM grade WHERE students_id = ?1")
    List<Grade> findByStudentID(Integer id);
}
