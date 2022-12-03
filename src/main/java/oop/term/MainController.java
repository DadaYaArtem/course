package oop.term;

import lombok.AllArgsConstructor;
import oop.term.users.User;
import oop.term.users.UserService;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.ModelAndView;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

@Controller
@AllArgsConstructor
public class MainController {
    UserService usersService;

    @GetMapping(value = "/")
    public ModelAndView showHomePage(){
        ModelAndView modelAndView = new ModelAndView("register");
        modelAndView.addObject("user", new User());
        return modelAndView;
    }

    @PostMapping("/register")
    public void processRegister(@RequestParam(name = "setEmail") String email,
                                @RequestParam(name = "setPassword") String password,
                                HttpServletResponse response) throws IOException {
        usersService.createUser(email, password);
        response.sendRedirect("login");
    }

}
