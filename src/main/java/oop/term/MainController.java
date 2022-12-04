package oop.term;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Controller;

@Controller
@RequiredArgsConstructor
public class MainController {

//    @GetMapping(value = "/")
//    public ModelAndView showHomePage(){
//        ModelAndView modelAndView = new ModelAndView("login");
//        modelAndView.addObject("user", new User());
//        return modelAndView;
//    }
//
//    @PostMapping("/register")
//    public void processRegister(@RequestParam(name = "setEmail") String email,
//                                @RequestParam(name = "setPassword") String password,
//                                HttpServletResponse response) throws IOException {
//        usersService.createUser(email, password);
//        User byEmail = usersService.findByEmail(email);
//        System.out.println(byEmail);
//        response.getWriter().write("user saved");
//    }

}
