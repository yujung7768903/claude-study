public class UserService {
    private final UserRepository userRepository;
    private final EmailService emailService;
    private final EventPublisher eventPublisher;

    public UserService(UserRepository userRepository,
                      EmailService emailService,
                      EventPublisher eventPublisher) {
        this.userRepository = userRepository;
        this.emailService = emailService;
        this.eventPublisher = eventPublisher;
    }

    public User createUser(String name, String email) {
        User user = new User(name, email);
        User savedUser = userRepository.save(user);
        emailService.sendWelcomeEmail(email, name);
        eventPublisher.publish(new UserCreatedEvent(savedUser));
        return savedUser;
    }
}
