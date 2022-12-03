package oop.term.users;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class UserService {
    private List<User> usersList = new ArrayList<>();

    public void createUser(String email, String password) {
        usersList.add(new User(1, email, password));
        System.out.println(usersList);
    }
}
