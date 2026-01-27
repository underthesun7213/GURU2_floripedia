package com.example.plant.data.remote.api

import com.example.plant.data.remote.dto.request.UserUpdateRequest
import com.example.plant.data.remote.dto.response.FavoriteCountResponse
import com.example.plant.data.remote.dto.response.FavoriteToggleResponse
import com.example.plant.data.remote.dto.response.MessageResponse
import com.example.plant.data.remote.dto.response.PlantCardDto
import com.example.plant.data.remote.dto.response.UserResponse
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface UserApi {

    /**
     * 내 프로필 조회
     */
    @GET("users/me")
    suspend fun getMyProfile(): Response<UserResponse>

    /**
     * 프로필 정보 수정
     */
    @PATCH("users/me")
    suspend fun updateProfile(
        @Body request: UserUpdateRequest
    ): Response<UserResponse>

    /**
     * 프로필 이미지 업로드
     */
    @Multipart
    @POST("users/me/profile-image")
    suspend fun uploadProfileImage(
        @Part file: MultipartBody.Part
    ): Response<UserResponse>

    /**
     * 찜하기/취소 토글
     */
    @POST("users/me/favorites/{plant_id}")
    suspend fun toggleFavorite(
        @Path("plant_id") plantId: String
    ): Response<FavoriteToggleResponse>

    /**
     * 내 찜 목록 조회
     */
    @GET("users/me/favorites")
    suspend fun getMyFavorites(
        @Query("sort_by") sortBy: String = "name",
        @Query("sort_order") sortOrder: String = "asc"
    ): Response<List<PlantCardDto>>

    /**
     * 내 찜 개수 조회
     */
    @GET("users/me/favorites/count")
    suspend fun getMyFavoritesCount(): Response<FavoriteCountResponse>

    /**
     * 로그아웃
     */
    @POST("users/logout")
    suspend fun logout(): Response<MessageResponse>

    /**
     * 회원 탈퇴
     */
    @DELETE("users/me")
    suspend fun deleteAccount(): Response<MessageResponse>
}
