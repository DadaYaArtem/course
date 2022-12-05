package oop.term;

import lombok.RequiredArgsConstructor;
import oop.term.model.Course;
import oop.term.model.Student;
import oop.term.model.User;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Optional;

@Controller
@RequiredArgsConstructor
public class MainController {
    private final StudentRepository studentRepository;

    @GetMapping(value = "/")
    public void showHomePage(HttpServletResponse response) throws IOException {
        Student odesa = studentRepository.findByAddress("Odesa");
        response.getWriter().write(String.valueOf(odesa));
    }
}
