package com.example.plant.data.remote.dto.response

import com.google.gson.annotations.SerializedName

/**
 * 식물 목록/카드용 경량 DTO
 */
data class PlantCardDto(
    @SerializedName("_id")
    val id: String,

    @SerializedName("name")
    val name: String,

    @SerializedName("flowerLanguage")
    val flowerLanguage: String,

    @SerializedName("imageUrl")
    val imageUrl: String?,

    @SerializedName("season")
    val season: String,

    @SerializedName("preContent")
    val preContent: String?
)

/**
 * 식물 상세 정보 DTO
 */
data class PlantDetailDto(
    @SerializedName("_id")
    val id: String,

    @SerializedName("name")
    val name: String,

    @SerializedName("scientificName")
    val scientificName: String,

    @SerializedName("isRepresentative")
    val isRepresentative: Boolean,

    @SerializedName("taxonomy")
    val taxonomy: TaxonomyDto,

    @SerializedName("horticulture")
    val horticulture: HorticultureDto,

    @SerializedName("habitat")
    val habitat: String,

    @SerializedName("flowerInfo")
    val flowerInfo: FlowerInfoDto,

    @SerializedName("stories")
    val stories: List<StoryDto>,

    @SerializedName("images")
    val images: List<String>,

    @SerializedName("imageUrl")
    val imageUrl: String?,

    @SerializedName("season")
    val season: String,

    @SerializedName("bloomingMonths")
    val bloomingMonths: List<Int>,

    @SerializedName("searchKeywords")
    val searchKeywords: List<String>,

    @SerializedName("popularityScore")
    val popularityScore: Int,

    @SerializedName("colorInfo")
    val colorInfo: ColorInfoDto,

    @SerializedName("scentInfo")
    val scentInfo: ScentInfoDto,

    @SerializedName("isFavorite")
    val isFavorite: Boolean = false
)

data class TaxonomyDto(
    @SerializedName("genus")
    val genus: String,

    @SerializedName("species")
    val species: String,

    @SerializedName("family")
    val family: String
)

data class HorticultureDto(
    @SerializedName("category")
    val category: String,

    @SerializedName("categoryGroup")
    val categoryGroup: String,

    @SerializedName("usage")
    val usage: List<String>,

    @SerializedName("management")
    val management: String?,

    @SerializedName("preContent")
    val preContent: String?
)

data class FlowerInfoDto(
    @SerializedName("language")
    val language: String,

    @SerializedName("flowerGroup")
    val flowerGroup: String
)

data class StoryDto(
    @SerializedName("genre")
    val genre: String,

    @SerializedName("content")
    val content: String
)

data class ColorInfoDto(
    @SerializedName("hexCodes")
    val hexCodes: List<String>,

    @SerializedName("colorLabels")
    val colorLabels: List<String>,

    @SerializedName("colorGroup")
    val colorGroup: List<String>
)

data class ScentInfoDto(
    @SerializedName("scentTags")
    val scentTags: List<String>,

    @SerializedName("scentGroup")
    val scentGroup: List<String>
)

/**
 * 탐색(추천) 결과 DTO
 */
data class PlantExploreDto(
    @SerializedName("_id")
    val id: String,

    @SerializedName("name")
    val name: String,

    @SerializedName("imageUrl")
    val imageUrl: String,

    @SerializedName("category")
    val category: String,

    @SerializedName("season")
    val season: String,

    @SerializedName("scentTags")
    val scentTags: List<String>,

    @SerializedName("hexCode")
    val hexCode: String,

    @SerializedName("colorLabel")
    val colorLabel: String,

    @SerializedName("recommendation")
    val recommendation: String
)

/**
 * 이미지 검색 결과 DTO
 */
data class PlantSearchResultDto(
    @SerializedName("_id")
    val id: String,

    @SerializedName("name")
    val name: String,

    @SerializedName("scientificName")
    val scientificName: String,

    @SerializedName("imageUrl")
    val imageUrl: String?,

    @SerializedName("season")
    val season: String,

    @SerializedName("isNewlyCreated")
    val isNewlyCreated: Boolean,

    @SerializedName("isFavorite")
    val isFavorite: Boolean
)

/**
 * 식물 개수 응답
 */
data class PlantCountResponse(
    @SerializedName("count")
    val count: Int
)
