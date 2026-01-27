package com.example.plant.data.remote.api

import com.example.plant.data.remote.dto.response.PlantCardDto
import com.example.plant.data.remote.dto.response.PlantCountResponse
import com.example.plant.data.remote.dto.response.PlantDetailDto
import com.example.plant.data.remote.dto.response.PlantExploreDto
import com.example.plant.data.remote.dto.response.PlantSearchResultDto
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface PlantApi {

    /**
     * 전체 식물 목록 조회 및 필터링
     */
    @GET("plants")
    suspend fun getPlants(
        @Query("season") season: String? = null,
        @Query("blooming_month") bloomingMonth: Int? = null,
        @Query("category_group") categoryGroup: String? = null,
        @Query("color_group") colorGroup: String? = null,
        @Query("scent_group") scentGroup: String? = null,
        @Query("flower_group") flowerGroup: String? = null,
        @Query("story_genre") storyGenre: String? = null,
        @Query("keyword") keyword: String? = null,
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20,
        @Query("sort_by") sortBy: String = "name",
        @Query("sort_order") sortOrder: String = "asc"
    ): Response<List<PlantCardDto>>

    /**
     * 필터 조건에 맞는 식물 총 개수
     */
    @GET("plants/count")
    suspend fun getPlantsCount(
        @Query("season") season: String? = null,
        @Query("blooming_month") bloomingMonth: Int? = null,
        @Query("category_group") categoryGroup: String? = null,
        @Query("color_group") colorGroup: String? = null,
        @Query("scent_group") scentGroup: String? = null,
        @Query("flower_group") flowerGroup: String? = null,
        @Query("story_genre") storyGenre: String? = null,
        @Query("keyword") keyword: String? = null
    ): Response<PlantCountResponse>

    /**
     * 내 꽃갈피(찜) 목록 조회
     */
    @GET("plants/favorites")
    suspend fun getFavorites(
        @Query("season") season: String? = null,
        @Query("category_group") categoryGroup: String? = null,
        @Query("color_group") colorGroup: String? = null,
        @Query("skip") skip: Int = 0,
        @Query("limit") limit: Int = 20
    ): Response<List<PlantCardDto>>

    /**
     * 식물 상세 정보 조회
     */
    @GET("plants/{plant_id}")
    suspend fun getPlantDetail(
        @Path("plant_id") plantId: String
    ): Response<PlantDetailDto>

    /**
     * 상황별 식물 추천 (AI)
     */
    @POST("plants/recommend")
    suspend fun recommendPlant(
        @Query("situation") situation: String
    ): Response<PlantExploreDto>

    /**
     * 이미지 기반 식물 검색
     */
    @Multipart
    @POST("plants/search/image")
    suspend fun searchByImage(
        @Part file: MultipartBody.Part
    ): Response<PlantSearchResultDto>
}
