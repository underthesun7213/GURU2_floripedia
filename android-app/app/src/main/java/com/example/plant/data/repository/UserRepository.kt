package com.example.plant.data.repository

import com.example.plant.data.remote.RetrofitClient
import com.example.plant.data.remote.dto.request.UserUpdateRequest
import com.example.plant.data.remote.dto.response.PlantCardDto
import com.example.plant.data.remote.dto.response.UserResponse
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

class UserRepository {

    private val api = RetrofitClient.userApi

    /**
     * 내 프로필 조회
     */
    suspend fun getMyProfile(): Result<UserResponse> {
        return try {
            val response = api.getMyProfile()
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("프로필 조회 실패: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 프로필 수정
     */
    suspend fun updateProfile(nickname: String?, profileImageUrl: String?): Result<UserResponse> {
        return try {
            val request = UserUpdateRequest(
                nickname = nickname,
                profileImageUrl = profileImageUrl
            )
            val response = api.updateProfile(request)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("프로필 수정 실패: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 프로필 이미지 업로드
     */
    suspend fun uploadProfileImage(imageData: ByteArray, fileName: String, contentType: String): Result<UserResponse> {
        return try {
            val requestBody = imageData.toRequestBody(contentType.toMediaTypeOrNull())
            val part = MultipartBody.Part.createFormData("file", fileName, requestBody)

            val response = api.uploadProfileImage(part)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("이미지 업로드 실패: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 찜하기/취소 토글
     */
    suspend fun toggleFavorite(plantId: String): Result<Boolean> {
        return try {
            val response = api.toggleFavorite(plantId)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.isFavorite)
            } else {
                Result.failure(Exception("찜 토글 실패: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 내 찜 목록 조회
     */
    suspend fun getMyFavorites(
        sortBy: String = "name",
        sortOrder: String = "asc"
    ): Result<List<PlantCardDto>> {
        return try {
            val response = api.getMyFavorites(sortBy, sortOrder)
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
     * 내 찜 개수 조회
     */
    suspend fun getMyFavoritesCount(): Result<Int> {
        return try {
            val response = api.getMyFavoritesCount()
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.count)
            } else {
                Result.failure(Exception("찜 개수 조회 실패"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 로그아웃
     */
    suspend fun logout(): Result<String> {
        return try {
            val response = api.logout()
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.message)
            } else {
                Result.failure(Exception("로그아웃 실패"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 회원 탈퇴
     */
    suspend fun deleteAccount(): Result<String> {
        return try {
            val response = api.deleteAccount()
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.message)
            } else {
                Result.failure(Exception("회원 탈퇴 실패"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
