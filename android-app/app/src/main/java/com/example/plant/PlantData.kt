package com.example.plant

import android.graphics.Color

class PlantData {}
/**
 * 1. 계절 정의 (Season Enum)
 */
enum class Season {
    SPRING, SUMMER, FALL, WINTER
}

/**
 * 2. 식물의 과학적 분류 (Taxonomy)

 */
data class Taxonomy(
    val genus: String,  // 속 ("장미속")
    val species: String // 종 ("장미")
)

/**
 * 3. 식물 정보 상세 모델 (Plant)
 */
data class Plant(
    /**
     * [plantId]
     * MongoDB Atlas에서 자동 생성되는 고유 ID (_id)를 사용합니다.
     */
    val plantId: String,

    val name: String,             // 한글 이름 (예: "빨간 장미")
    val scientificName: String,   // 학명 (영문/라틴어만: "Rosa hybrida")
    val isRepresentative: Boolean, // 대표종/대표색 여부
    val taxonomy: Taxonomy,       // 과학적 분류 (한글)
    val habitat: String,          // 서식지 (한글 설명)
    val flowerLanguage: String,   // 꽃말 (한글)
    val story: String,            // 식물 이야기 (한글)
    val birthDate: List<String>,  // 탄생화 날짜 (MM-DD)
    val imageUrl: String,         // 이미지 URL
    val hexCode: String,          // 대표 색상 (16진수)
    val season: Season,           // 계절 (Enum)
    val bloomingMonths: List<Int>, // 개화 월 (1~12)
    val scentTags: List<String>,  // 향기 태그 (한글)
    val searchKeywords: List<String> // 검색 통합 키워드
)


/**
 * [UI 확장 기능]
 * 헥사 코드를 안드로이드 컬러 값으로 변환
 */
fun Plant.getBackgroundColor(): Int {
    return try {
        Color.parseColor(this.hexCode)
    } catch (e: Exception) {
        Color.WHITE
    }
}