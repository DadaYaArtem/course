package oop.term.controller;

import lombok.RequiredArgsConstructor;
import oop.term.model.Mentor;
import oop.term.repository.MentorsRepository;
import oop.term.service.StudentService;
import oop.term.model.Grade;
import oop.term.repository.GradeRepository;
import oop.term.repository.StudentRepository;
import oop.term.model.Student;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.ModelAndView;

import javax.persistence.EntityNotFoundException;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;

@Controller
@RequiredArgsConstructor
public class MainController {
    private final StudentRepository studentRepository;
    private final GradeRepository gradeRepository;
    private final MentorsRepository mentorsRepository;

    @GetMapping(value = "/")
    public ModelAndView showHomePage() throws IOException {
        ModelAndView modelAndView = new ModelAndView("main");
//        List<Student> stList = studentRepository.findAll();
//        modelAndView.addObject("stList", stList);
        return modelAndView;
    }

    @GetMapping(value = "/students")
    public ModelAndView showStudentsList(){
        ModelAndView modelAndView = new ModelAndView("students-list");
        List<Student> stList = studentRepository.findAll();
        for (Student student : stList) {
            student.setAvgGrade(StudentService.getAvgGrade(gradeRepository.findByStudentID(student.getId())));
        }

        modelAndView.addObject("exSt", StudentService.getExcStudents(stList));
        modelAndView.addObject("bdSt", StudentService.getBadStudents(stList));

        modelAndView.addObject("stList", stList);
        return modelAndView;
    }

    @GetMapping("/mentors")
    public ModelAndView showMentorsList(){
        ModelAndView modelAndView = new ModelAndView("mentors-list");
        List<Mentor> mntList = mentorsRepository.findAll();
        System.out.println("mntList = " + mntList);

        modelAndView.addObject("mntList", mntList);

        return modelAndView;
    }

    @GetMapping(value = "students/grade")
    public ModelAndView showStudentGrade(@RequestParam(name = "id") Integer id,
                                         HttpServletResponse response) throws IOException {
        ModelAndView modelAndView = new ModelAndView("student-grade");
        try {
            Student byId = studentRepository.getReferenceById(id);
            List<Grade> gradeList = byId.getGradeList();
            int avgGrade = StudentService.getAvgGrade(gradeList);

            System.out.println("avgGrade = " + avgGrade);
            System.out.println("id = " + id);
            System.out.println("byId = " + byId);

            modelAndView.addObject("grades", gradeList);
            modelAndView.addObject("avg", avgGrade);
            return modelAndView;
        }catch (EntityNotFoundException e){
            response.getWriter().write("No such student");
            return null;
        }

    }
}
