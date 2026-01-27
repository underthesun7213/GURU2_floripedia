package com.example.plant.data.repository

import com.example.plant.data.remote.RetrofitClient
import com.example.plant.data.remote.dto.response.PlantCardDto
import com.example.plant.data.remote.dto.response.PlantDetailDto
import com.example.plant.data.remote.dto.response.PlantExploreDto
import com.example.plant.data.remote.dto.response.PlantSearchResultDto
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

class PlantRepository {

    private val api = RetrofitClient.plantApi

    /**
     * 식물 목록 조회 (필터링 지원)
     */
    suspend fun getPlants(
        season: String? = null,
        bloomingMonth: Int? = null,
        categoryGroup: String? = null,
        colorGroup: String? = null,
        scentGroup: String? = null,
        flowerGroup: String? = null,
        storyGenre: String? = null,
        keyword: String? = null,
        skip: Int = 0,
        limit: Int = 20,
        sortBy: String = "name",
        sortOrder: String = "asc"
    ): Result<List<PlantCardDto>> {
        return try {
            val response = api.getPlants(
                season = season,
                bloomingMonth = bloomingMonth,
                categoryGroup = categoryGroup,
                colorGroup = colorGroup,
                scentGroup = scentGroup,
                flowerGroup = flowerGroup,
                storyGenre = storyGenre,
                keyword = keyword,
                skip = skip,
                limit = limit,
                sortBy = sortBy,
                sortOrder = sortOrder
            )
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("식물 목록 조회 실패: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 식물 개수 조회
     */
    suspend fun getPlantsCount(
        season: String? = null,
        bloomingMonth: Int? = null,
        categoryGroup: String? = null,
        colorGroup: String? = null,
        scentGroup: String? = null,
        flowerGroup: String? = null,
        storyGenre: String? = null,
        keyword: String? = null
    ): Result<Int> {
        return try {
            val response = api.getPlantsCount(
                season = season,
                bloomingMonth = bloomingMonth,
                categoryGroup = categoryGroup,
                colorGroup = colorGroup,
                scentGroup = scentGroup,
                flowerGroup = flowerGroup,
                storyGenre = storyGenre,
                keyword = keyword
            )
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.count)
            } else {
                Result.failure(Exception("식물 개수 조회 실패"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 꽃갈피(찜) 목록 조회
     */
    suspend fun getFavorites(
        season: String? = null,
        categoryGroup: String? = null,
        colorGroup: String? = null,
        skip: Int = 0,
        limit: Int = 20
    ): Result<List<PlantCardDto>> {
        return try {
            val response = api.getFavorites(
                season = season,
                categoryGroup = categoryGroup,
                colorGroup = colorGroup,
                skip = skip,
                limit = limit
            )
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("찜 목록 조회 실패: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 식물 상세 정보 조회
     */
    suspend fun getPlantDetail(plantId: String): Result<PlantDetailDto> {
        return try {
            val response = api.getPlantDetail(plantId)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("식물 상세 조회 실패: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 상황별 식물 추천 (AI)
     */
    suspend fun recommendPlant(situation: String): Result<PlantExploreDto> {
        return try {
            val response = api.recommendPlant(situation)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("추천 실패: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 이미지로 식물 검색
     */
    suspend fun searchByImage(imageData: ByteArray, fileName: String): Result<PlantSearchResultDto> {
        return try {
            val requestBody = imageData.toRequestBody("image/*".toMediaTypeOrNull())
            val part = MultipartBody.Part.createFormData("file", fileName, requestBody)

            val response = api.searchByImage(part)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("이미지 검색 실패: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
