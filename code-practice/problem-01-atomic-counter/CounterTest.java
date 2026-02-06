import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * Counter 구현체들을 테스트하는 클래스
 */
public class CounterTest {

    public static void main(String[] args) throws InterruptedException {
        System.out.println("========================================");
        System.out.println("  멀티스레드 카운터 테스트");
        System.out.println("========================================\n");

        // 1. 단일 스레드 테스트
        testSingleThread();

        // 2. 멀티스레드 테스트 (race condition 확인)
        testMultiThread();

        // 3. 성능 비교
        testPerformance();

        System.out.println("\n========================================");
        System.out.println("  모든 테스트 완료!");
        System.out.println("========================================");
    }

    /**
     * 단일 스레드 환경에서 정상 동작 확인
     */
    private static void testSingleThread() {
        System.out.println("=== 1. 단일 스레드 테스트 (각 1000번 증가) ===\n");

        Counter[] counters = {
            new UnsafeCounter(),
            new SynchronizedCounter(),
            new AtomicCounter()
        };

        String[] names = {"UnsafeCounter", "SynchronizedCounter", "AtomicCounter"};

        for (int i = 0; i < counters.length; i++) {
            Counter counter = counters[i];
            for (int j = 0; j < 1000; j++) {
                counter.increment();
            }
            int count = counter.getCount();
            String status = (count == 1000) ? "✅" : "❌";
            System.out.println(names[i] + ": " + count + " " + status);
        }

        System.out.println();
    }

    /**
     * 멀티스레드 환경에서 race condition 확인
     */
    private static void testMultiThread() throws InterruptedException {
        System.out.println("=== 2. 멀티스레드 테스트 (10개 스레드, 각 1000번 증가) ===\n");
        System.out.println("예상 결과: 10000\n");

        int threadCount = 10;
        int incrementsPerThread = 1000;
        int expectedCount = threadCount * incrementsPerThread;

        Counter[] counters = {
            new UnsafeCounter(),
            new SynchronizedCounter(),
            new AtomicCounter()
        };

        String[] names = {"UnsafeCounter", "SynchronizedCounter", "AtomicCounter"};

        for (int i = 0; i < counters.length; i++) {
            Counter counter = counters[i];
            counter.reset();

            // ExecutorService로 스레드 풀 생성
            ExecutorService executor = Executors.newFixedThreadPool(threadCount);
            CountDownLatch latch = new CountDownLatch(threadCount);

            // 각 스레드에서 increment 실행
            for (int t = 0; t < threadCount; t++) {
                executor.submit(() -> {
                    for (int j = 0; j < incrementsPerThread; j++) {
                        counter.increment();
                    }
                    latch.countDown();
                });
            }

            // 모든 스레드가 완료될 때까지 대기
            latch.await();
            executor.shutdown();

            int actualCount = counter.getCount();
            String status = (actualCount == expectedCount) ? "✅" : "❌";
            System.out.println(names[i] + ": " + actualCount + " " + status);
        }

        System.out.println();
    }

    /**
     * synchronized vs AtomicInteger 성능 비교
     */
    private static void testPerformance() throws InterruptedException {
        System.out.println("=== 3. 성능 비교 (10개 스레드, 각 100000번 증가) ===\n");

        int threadCount = 10;
        int incrementsPerThread = 100000;

        // SynchronizedCounter 성능 측정
        Counter syncCounter = new SynchronizedCounter();
        long syncTime = measurePerformance(syncCounter, threadCount, incrementsPerThread);
        System.out.println("SynchronizedCounter: " + syncTime + "ms");

        // AtomicCounter 성능 측정
        Counter atomicCounter = new AtomicCounter();
        long atomicTime = measurePerformance(atomicCounter, threadCount, incrementsPerThread);
        System.out.println("AtomicCounter: " + atomicTime + "ms");

        // 성능 비교
        double ratio = (double) syncTime / atomicTime;
        System.out.println("\n→ AtomicCounter가 약 " + String.format("%.1f", ratio) + "배 빠름");
    }

    /**
     * 성능 측정 헬퍼 메서드
     */
    private static long measurePerformance(Counter counter, int threadCount, int incrementsPerThread)
            throws InterruptedException {
        counter.reset();

        long startTime = System.currentTimeMillis();

        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch latch = new CountDownLatch(threadCount);

        for (int t = 0; t < threadCount; t++) {
            executor.submit(() -> {
                for (int j = 0; j < incrementsPerThread; j++) {
                    counter.increment();
                }
                latch.countDown();
            });
        }

        latch.await();
        executor.shutdown();

        long endTime = System.currentTimeMillis();
        return endTime - startTime;
    }
}
