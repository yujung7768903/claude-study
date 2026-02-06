import java.util.concurrent.atomic.AtomicInteger;

/**
 * AtomicInteger를 사용한 lock-free thread-safe 카운터
 */
public class AtomicCounter implements Counter {

    // TODO: AtomicInteger 필드 선언 및 초기화


    @Override
    public void increment() {
        // TODO: AtomicInteger의 메서드를 사용하여 1 증가

    }

    @Override
    public int getCount() {
        // TODO: AtomicInteger의 현재 값 반환
        return 0;
    }

    @Override
    public void reset() {
        // TODO: AtomicInteger를 0으로 초기화

    }
}
