package oop.term.repository;

import oop.term.model.Grade;
import oop.term.model.Mentor;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MentorsRepository extends JpaRepository<Mentor, Integer> {
}
