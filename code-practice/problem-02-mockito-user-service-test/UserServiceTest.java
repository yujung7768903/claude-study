import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.MockitoJUnitRunner;

import static org.junit.Assert.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@RunWith(MockitoJUnitRunner.class)
public class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private EmailService emailService;

    @Mock
    private EventPublisher eventPublisher;

    @InjectMocks
    private UserService userService;

    @Test
    public void 사용자_생성_성공_테스트() {
        // given
        String name = "john";
        String email = "john@example.com";
        User mockUser = new User(1L, name, email);
        when(userRepository.save(any(User.class)))
                .thenReturn(mockUser);

        // when
        User result = userService.createUser(name, email);

        // then
        // TODO: 반환된 User가 null이 아닌지 검증
        assertNotNull(result);
        // TODO: User의 name이 "john"인지 검증
        assertEquals(name, result.getName());
        // TODO: User의 email이 "john@example.com"인지 검증
        assertEquals(email, result.getEmail());
        // TODO: userRepository.save()가 1번 호출되었는지 검증
        // 힌트: verify()로 mock 객체의 특정 메서드 호출 여부를 검증하세요


        // TODO: emailService.sendWelcomeEmail()이 1번 호출되었는지 검증


        // TODO: eventPublisher.publish()가 1번 호출되었는지 검증

    }

    @Test
    public void 사용자_생성시_올바른_이메일_파라미터_전달_확인() {
        // given
        User mockUser = new User(1L, "john", "john@example.com");
        when(userRepository.save(any(User.class))).thenReturn(mockUser);

        // when
        userService.createUser("john", "john@example.com");

        // then
        // TODO: ArgumentCaptor<String> 2개 생성 (email, userName용)
        // 힌트: ArgumentCaptor.forClass()로 캡처할 타입을 지정하세요



        // TODO: verify()와 capture()를 사용하여 sendWelcomeEmail에 전달된 파라미터 캡처
        // ⚠️ 주의: 파라미터 일부만 Matcher를 쓰면 에러 납니다. 모든 파라미터를 통일하세요


        // TODO: 캡처한 email 값 가져오기
        String capturedEmail = null; // 이 부분을 구현하세요


        // TODO: 캡처한 userName 값 가져오기
        String capturedName = null; // 이 부분을 구현하세요


        // TODO: 캡처한 email이 "john@example.com"인지 검증


        // TODO: 캡처한 userName이 "john"인지 검증

    }

    @Test
    public void 사용자_생성시_이벤트에_올바른_사용자_정보_포함_확인() {
        // given
        User mockUser = new User(1L, "john", "john@example.com");
        when(userRepository.save(any(User.class))).thenReturn(mockUser);

        // when
        userService.createUser("john", "john@example.com");

        // then
        // TODO: ArgumentCaptor<UserCreatedEvent> 생성



        // TODO: verify()와 capture()를 사용하여 publish에 전달된 이벤트 캡처


        // TODO: 캡처한 이벤트 가져오기
        UserCreatedEvent capturedEvent = null; // 이 부분을 구현하세요


        // TODO: 이벤트의 User가 null이 아닌지 검증


        // TODO: 이벤트의 User name이 "john"인지 검증


        // TODO: 이벤트의 User email이 "john@example.com"인지 검증

    }
}
