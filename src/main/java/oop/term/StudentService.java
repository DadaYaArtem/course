package oop.term;

import oop.term.model.Grade;
import oop.term.model.Student;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class StudentService {
    public static int getAvgGrade(List<Grade> grades){
        if (grades.size() == 0){
            return 0;
        }
        int max = 0;
        for (Grade grade : grades) {
            max += grade.getGrade();
        }

        return max / grades.size();
    }

    public static int getExcStudents(List<Student> students){
        int result = 0;

        for (Student student : students) {
            int avgGrade = getAvgGrade(student.getGradeList());
            if (avgGrade >= 90){
                result++;
            }
        }

        return result;
    }

    public static int getBadStudents(List<Student> students){
        int result = 0;

        for (Student student : students) {
            int avgGrade = getAvgGrade(student.getGradeList());
            if (avgGrade <= 90){
                result++;
            }
        }

        return result;
    }
}
