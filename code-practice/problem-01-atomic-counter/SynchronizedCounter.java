/**
 * synchronized를 사용한 thread-safe 카운터
 */
public class SynchronizedCounter implements Counter {

    // TODO: int 필드 선언
    private int count = 0;
    @Override
    public synchronized void increment() {
        // TODO: synchronized로 동기화하여 count를 1 증가
        count++;
    }

    @Override
    public synchronized int getCount() {
        // TODO: synchronized로 동기화하여 현재 count 값 반환
        return count;
    }

    @Override
    public synchronized void reset() {
        // TODO: synchronized로 동기화하여 count를 0으로 초기화
        this.count = 0;
    }
}
