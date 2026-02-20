import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.MockitoJUnitRunner;

import static org.junit.Assert.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

// TODO: @RunWith 어노테이션 추가
public class UserServiceTest {

    // TODO: UserRepository를 @Mock으로 선언


    // TODO: EmailService를 @Mock으로 선언


    // TODO: EventPublisher를 @Mock으로 선언


    // TODO: UserService를 @InjectMocks로 선언하여 의존성 자동 주입


    @Test
    public void 사용자_생성_성공_테스트() {
        // given
        // TODO: userRepository.save() 호출 시 반환할 mock User 객체 생성
        User mockUser = new User(1L, "john", "john@example.com");

        // TODO: when().thenReturn()을 사용하여 userRepository.save() stubbing
        // 힌트: when(userRepository.save(any(User.class))).thenReturn(mockUser);


        // when
        // TODO: userService.createUser() 호출
        User result = null; // 이 부분을 구현하세요


        // then
        // TODO: 반환된 User가 null이 아닌지 검증


        // TODO: User의 name이 "john"인지 검증


        // TODO: User의 email이 "john@example.com"인지 검증


        // TODO: userRepository.save()가 1번 호출되었는지 검증
        // 힌트: verify(userRepository).save(any(User.class));


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
        // 힌트: ArgumentCaptor<String> emailCaptor = ArgumentCaptor.forClass(String.class);



        // TODO: verify()와 capture()를 사용하여 sendWelcomeEmail에 전달된 파라미터 캡처
        // 힌트: verify(emailService).sendWelcomeEmail(emailCaptor.capture(), nameCaptor.capture());
        // ⚠️ 주의: 모든 파라미터를 Matcher로 감싸야 합니다!


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
        // 힌트: verify(eventPublisher).publish(eventCaptor.capture());


        // TODO: 캡처한 이벤트 가져오기
        UserCreatedEvent capturedEvent = null; // 이 부분을 구현하세요


        // TODO: 이벤트의 User가 null이 아닌지 검증


        // TODO: 이벤트의 User name이 "john"인지 검증


        // TODO: 이벤트의 User email이 "john@example.com"인지 검증

    }
}
