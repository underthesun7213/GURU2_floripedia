package com.example.plant.data.model

import com.example.plant.R

/**
 * 필터 카테고리 모델
 */
data class FilterCategory(
    val name: String,              // 표시 이름 (예: "봄", "꽃과 풀")
    val imageRes: Int,             // 아이콘 리소스
    val filterType: FilterType,     // 필터 타입
    val filterValue: String,        // 백엔드로 전송할 값
    val isSelected: Boolean = false // 선택 상태
)

/**
 * 필터 타입 정의
 */
enum class FilterType {
    SEASON,           // 계절 (SPRING, SUMMER, FALL, WINTER)
    CATEGORY_GROUP,   // 식물 분류 (꽃과 풀, 나무와 조경, 실내 인테리어, 텃밭과 정원)
    COLOR_GROUP,      // 색상 그룹 (백색/미색, 노랑/주황, 빨강/분홍, 푸른색, 갈색/검정)
    SCENT_GROUP,      // 향기 그룹 (달콤·화사, 싱그러운·시원, 은은·차분, 무향)
    FLOWER_GROUP,     // 꽃말 그룹 (사랑/고백, 위로/슬픔, 감사/존경, 이별/그리움, 행복/즐거움)
    STORY_GENRE       // 이야기 장르
}

/**
 * 필터 데이터 생성을 위한 팩토리 (Rich Domain 모델 지향)
 */
object FilterCategoryFactory {
    fun createDefaultFilters(): List<FilterCategory> {
        val data = mutableListOf<FilterCategory>()
        
        // 0. 개화시기
        data.add(FilterCategory("봄", R.drawable.spring, FilterType.SEASON, "SPRING"))
        data.add(FilterCategory("여름", R.drawable.summer, FilterType.SEASON, "SUMMER"))
        data.add(FilterCategory("가을", R.drawable.autumn, FilterType.SEASON, "FALL"))
        data.add(FilterCategory("겨울", R.drawable.winter, FilterType.SEASON, "WINTER"))

        // 1. 꽃말 그룹
        data.add(FilterCategory("사랑/고백", R.drawable.love, FilterType.FLOWER_GROUP, "사랑/고백"))
        data.add(FilterCategory("위로/슬픔", R.drawable.sad, FilterType.FLOWER_GROUP, "위로/슬픔"))
        data.add(FilterCategory("감사/존경", R.drawable.thanks, FilterType.FLOWER_GROUP, "감사/존경"))
        data.add(FilterCategory("이별/그리움", R.drawable.missing, FilterType.FLOWER_GROUP, "이별/그리움"))
        data.add(FilterCategory("행복/즐거움", R.drawable.happy, FilterType.FLOWER_GROUP, "행복/즐거움"))

        // 2. 향기 그룹
        data.add(FilterCategory("달콤·화사", R.drawable.sweet, FilterType.SCENT_GROUP, "달콤·화사"))
        data.add(FilterCategory("싱그러운·시원", R.drawable.fresh, FilterType.SCENT_GROUP, "싱그러운·시원"))
        data.add(FilterCategory("은은·차분", R.drawable.soft, FilterType.SCENT_GROUP, "은은·차분"))
        data.add(FilterCategory("무향", R.drawable.unscented, FilterType.SCENT_GROUP, "무향"))

        // 3. 식물 분류 그룹
        data.add(FilterCategory("꽃과 풀", R.drawable.flower, FilterType.CATEGORY_GROUP, "꽃과 풀"))
        data.add(FilterCategory("나무와 조경", R.drawable.tree, FilterType.CATEGORY_GROUP, "나무와 조경"))
        data.add(FilterCategory("실내 인테리어", R.drawable.interior, FilterType.CATEGORY_GROUP, "실내 인테리어"))
        data.add(FilterCategory("텃밭과 정원", R.drawable.garden, FilterType.CATEGORY_GROUP, "텃밭과 정원"))

        // 4. 색상 그룹
        data.add(FilterCategory("백색/미색", R.drawable.white, FilterType.COLOR_GROUP, "백색/미색"))
        data.add(FilterCategory("노랑/주황", R.drawable.yellow, FilterType.COLOR_GROUP, "노랑/주황"))
        data.add(FilterCategory("빨강/분홍", R.drawable.red, FilterType.COLOR_GROUP, "빨강/분홍"))
        data.add(FilterCategory("푸른색", R.drawable.blue, FilterType.COLOR_GROUP, "푸른색"))
        data.add(FilterCategory("갈색/검정", R.drawable.black, FilterType.COLOR_GROUP, "갈색/검정"))

        return data
    }
}

/**
 * 필터 값 Validation
 */
object FilterValidator {
    private val validSeasons = setOf("SPRING", "SUMMER", "FALL", "WINTER")
    private val validCategoryGroups = setOf("꽃과 풀", "나무와 조경", "실내 인테리어", "텃밭과 정원")
    private val validColorGroups = setOf("백색/미색", "노랑/주황", "빨강/분홍", "푸른색", "갈색/검정")
    private val validScentGroups = setOf("달콤·화사", "싱그러운·시원", "은은·차분", "무향")
    private val validFlowerGroups = setOf("사랑/고백", "위로/슬픔", "감사/존경", "이별/그리움", "행복/즐거움")
    
    /**
     * 필터 값이 유효한지 검증
     */
    fun isValid(filterType: FilterType, value: String): Boolean {
        return when (filterType) {
            FilterType.SEASON -> validSeasons.contains(value)
            FilterType.CATEGORY_GROUP -> validCategoryGroups.contains(value)
            FilterType.COLOR_GROUP -> validColorGroups.contains(value)
            FilterType.SCENT_GROUP -> validScentGroups.contains(value)
            FilterType.FLOWER_GROUP -> validFlowerGroups.contains(value)
            FilterType.STORY_GENRE -> true
        }
    }
    
    /**
     * 필터 타입별 유효한 값 목록 반환
     */
    fun getValidValues(filterType: FilterType): Set<String> {
        return when (filterType) {
            FilterType.SEASON -> validSeasons
            FilterType.CATEGORY_GROUP -> validCategoryGroups
            FilterType.COLOR_GROUP -> validColorGroups
            FilterType.SCENT_GROUP -> validScentGroups
            FilterType.FLOWER_GROUP -> validFlowerGroups
            FilterType.STORY_GENRE -> emptySet()
        }
    }
}
