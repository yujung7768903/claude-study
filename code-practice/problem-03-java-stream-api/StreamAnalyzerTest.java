import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * StreamAnalyzerImpl 검증 테스트.
 * 이 파일은 수정하지 마세요.
 */
public class StreamAnalyzerTest {

    private static int passed = 0;
    private static int failed = 0;

    public static void main(String[] args) {
        List<Product> products = createTestData();
        StreamAnalyzer analyzer = new StreamAnalyzerImpl(products);

        testExpensiveProducts(analyzer);
        testProductNamesByCategory(analyzer);
        testTotalStockByCategory(analyzer);
        testAveragePriceByCategory(analyzer);
        testMostExpensiveProduct(analyzer);
        testProductCountByCategory(analyzer);
        testAllTags(analyzer);
        testTopNByPrice(analyzer);
        testHasOutOfStockProduct(analyzer);
        testTotalRevenuePotential(analyzer);

        System.out.println("\n" + "=".repeat(40));
        System.out.printf("결과: %d개 통과 / %d개 실패%n", passed, failed);
        if (failed == 0) {
            System.out.println("✅ 모든 테스트 통과!");
        } else {
            System.out.println("❌ 실패한 테스트가 있습니다. 구현을 확인하세요.");
        }
    }

    // ──────────────────────────────────────────────
    // 테스트 케이스
    // ──────────────────────────────────────────────

    private static void testExpensiveProducts(StreamAnalyzer analyzer) {
        System.out.println("\n=== 5만원 이상 상품 (가격 내림차순) ===");
        List<Product> result = analyzer.getExpensiveProducts(50000);
        System.out.println(result);

        if (result == null) { assertFail("5만원 이상 상품 수 (null 반환됨)"); return; }
        assertTrue("5만원 이상 상품 수", result.size() == 8);
        assertTrue("첫 번째 상품이 가장 비쌈", result.get(0).getName().equals("맥북 에어"));
        assertTrue("마지막 상품이 가장 저렴", result.get(result.size() - 1).getPrice() >= 50000);
        for (int i = 0; i < result.size() - 1; i++) {
            assertTrue("가격 내림차순 정렬", result.get(i).getPrice() >= result.get(i + 1).getPrice());
        }
    }

    private static void testProductNamesByCategory(StreamAnalyzer analyzer) {
        System.out.println("\n=== 전자제품 카테고리 상품명 (오름차순) ===");
        List<String> result = analyzer.getProductNamesByCategory("전자제품");
        System.out.println(result);

        if (result == null) { assertFail("전자제품 수 (null 반환됨)"); return; }
        assertTrue("전자제품 수", result.size() == 4);
        assertTrue("오름차순 첫 번째", result.get(0).equals("맥북 에어"));
        for (int i = 0; i < result.size() - 1; i++) {
            assertTrue("이름 오름차순", result.get(i).compareTo(result.get(i + 1)) <= 0);
        }
    }

    private static void testTotalStockByCategory(StreamAnalyzer analyzer) {
        System.out.println("\n=== 카테고리별 총 재고 ===");
        Map<String, Integer> result = analyzer.getTotalStockByCategory();
        System.out.println(result);

        if (result == null) { assertFail("카테고리별 재고 (null 반환됨)"); return; }
        assertTrue("카테고리 수", result.size() == 3);
        assertTrue("전자제품 재고 합계", result.get("전자제품") == 130);
        assertTrue("의류 재고 합계", result.get("의류") == 250);
        assertTrue("식품 재고 합계", result.get("식품") == 500);
    }

    private static void testAveragePriceByCategory(StreamAnalyzer analyzer) {
        System.out.println("\n=== 카테고리별 평균 가격 ===");
        Map<String, Integer> result = analyzer.getAveragePriceByCategory();
        if (result == null) { assertFail("카테고리별 평균가격 (null 반환됨)"); return; }
        result.forEach((k, v) -> System.out.println(k + ": " + v + "원"));

        assertTrue("전자제품 평균가격", result.get("전자제품") == 747500);
        assertTrue("의류 평균가격", result.get("의류") == 91333);
        assertTrue("식품 평균가격", result.get("식품") == 20000);
    }

    private static void testMostExpensiveProduct(StreamAnalyzer analyzer) {
        System.out.println("\n=== 가장 비싼 상품 ===");
        Optional<Product> result = analyzer.getMostExpensiveProduct();
        if (result == null) { assertFail("가장 비싼 상품 (null 반환됨)"); return; }
        result.ifPresent(p -> System.out.println(p.getName() + " (" + p.getPrice() + "원)"));

        assertTrue("가장 비싼 상품 존재", result.isPresent());
        if (result.isPresent()) {
            assertTrue("가장 비싼 상품명", result.get().getName().equals("맥북 에어"));
            assertTrue("가장 비싼 상품 가격", result.get().getPrice() == 1200000);
        }
    }

    private static void testProductCountByCategory(StreamAnalyzer analyzer) {
        System.out.println("\n=== 카테고리별 상품 수 ===");
        Map<String, Long> result = analyzer.getProductCountByCategory();
        System.out.println(result);

        if (result == null) { assertFail("카테고리별 상품 수 (null 반환됨)"); return; }
        assertTrue("전자제품 상품 수", result.get("전자제품") == 4L);
        assertTrue("의류 상품 수", result.get("의류") == 3L);
        assertTrue("식품 상품 수", result.get("식품") == 3L);
    }

    private static void testAllTags(StreamAnalyzer analyzer) {
        System.out.println("\n=== 전체 태그 (중복 제거, 정렬) ===");
        List<String> result = analyzer.getAllTags();
        System.out.println(result);

        if (result == null) { assertFail("전체 태그 (null 반환됨)"); return; }
        assertTrue("태그 중복 없음 - 개수 확인", result.size() == 15);
        assertTrue("태그 정렬 확인 - 첫 번째", result.get(0).equals("가성비"));
        assertTrue("태그 정렬 확인 - 마지막", result.get(result.size() - 1).equals("할인"));
        for (int i = 0; i < result.size() - 1; i++) {
            assertTrue("태그 오름차순", result.get(i).compareTo(result.get(i + 1)) <= 0);
        }
    }

    private static void testTopNByPrice(StreamAnalyzer analyzer) {
        System.out.println("\n=== 가격 상위 3개 상품명 ===");
        List<String> result = analyzer.getTopNByPrice(3);
        System.out.println(result);

        if (result == null) { assertFail("가격 상위 3개 (null 반환됨)"); return; }
        assertTrue("상위 3개 크기", result.size() == 3);
        assertTrue("1위 상품", result.get(0).equals("맥북 에어"));
        assertTrue("2위 상품", result.get(1).equals("아이폰 15"));
        assertTrue("3위 상품", result.get(2).equals("삼성 TV"));
    }

    private static void testHasOutOfStockProduct(StreamAnalyzer analyzer) {
        System.out.println("\n=== 품절 상품 존재 여부 ===");
        boolean result = analyzer.hasOutOfStockProduct();
        System.out.println(result);

        assertTrue("품절 상품 있음", result == true);
    }

    private static void testTotalRevenuePotential(StreamAnalyzer analyzer) {
        System.out.println("\n=== 전체 판매 가능 금액 ===");
        long result = analyzer.getTotalRevenuePotential();
        System.out.printf("%,d원%n", result);

        assertTrue("총 판매 가능 금액", result == 136_170_000L);
    }

    // ──────────────────────────────────────────────
    // 테스트 데이터
    // ──────────────────────────────────────────────

    private static List<Product> createTestData() {
        return Arrays.asList(
            // 전자제품
            new Product("아이폰 15",   "전자제품", 900_000, 50,  Arrays.asList("스마트폰", "모바일", "브랜드")),
            new Product("맥북 에어",   "전자제품", 1_200_000, 30, Arrays.asList("노트북", "브랜드", "할인")),
            new Product("삼성 TV",     "전자제품", 800_000, 20,  Arrays.asList("국산", "할인")),
            new Product("애플워치",    "전자제품", 90_000, 30,   Arrays.asList("스마트워치", "모바일", "브랜드")),
            // 의류
            new Product("나이키 운동화", "의류",  120_000, 100, Arrays.asList("브랜드", "가성비", "여름")),
            new Product("리바이스 청바지","의류", 89_000, 80,   Arrays.asList("브랜드", "캐주얼", "봄")),
            new Product("아디다스 후드", "의류",  65_000, 70,   Arrays.asList("브랜드", "겨울", "캐주얼")),
            // 식품
            new Product("스타벅스 원두", "식품",  52_000, 200, Arrays.asList("커피", "가성비")),
            new Product("유기농 사과",   "식품",  8_000, 300,  Arrays.asList("유기농", "국산")),
            new Product("닭가슴살",      "식품",  0, 0,         Arrays.asList("단백질", "가성비", "국산"))  // 품절 + 가격 0
        );
    }

    // ──────────────────────────────────────────────
    // 헬퍼
    // ──────────────────────────────────────────────

    private static void assertTrue(String testName, boolean condition) {
        if (condition) {
            System.out.println("  ✅ " + testName);
            passed++;
        } else {
            System.out.println("  ❌ " + testName + " (실패)");
            failed++;
        }
    }

    private static void assertFail(String testName) {
        System.out.println("  ❌ " + testName);
        failed++;
    }
}
