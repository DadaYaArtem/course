package oop.term.controller;

import lombok.RequiredArgsConstructor;
import oop.term.repository.StudentRepository;
import oop.term.model.Student;
import org.springframework.boot.Banner;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.ModelAndView;

import java.io.IOException;
import java.util.List;

@Controller
@RequiredArgsConstructor
public class MainController {
    private final StudentRepository studentRepository;

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
            System.out.println(student.getGradeList());
        }

        modelAndView.addObject("stList", stList);
        return modelAndView;
    }

    @GetMapping(value = "students/grade")
    public ModelAndView showStudentGrade(@RequestParam(name = "id") Integer id){
        ModelAndView modelAndView = new ModelAndView("student-grade");
        Student byId = studentRepository.getReferenceById(id);
        System.out.println("id = " + id);
        System.out.println("byId = " + byId);
        modelAndView.addObject("grades", byId.getGradeList());
        return modelAndView;
    }
}
