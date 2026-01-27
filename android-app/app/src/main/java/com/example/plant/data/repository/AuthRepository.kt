package com.example.plant.data.repository

import com.example.plant.data.remote.RetrofitClient
import com.example.plant.data.remote.TokenManager
import com.example.plant.data.remote.dto.request.LoginRequest
import com.example.plant.data.remote.dto.response.UserResponse

class AuthRepository {

    private val api = RetrofitClient.authApi

    /**
     * Firebase ID Token으로 로그인/회원가입
     */
    suspend fun login(idToken: String): Result<UserResponse> {
        return try {
            // Token 저장
            TokenManager.setToken(idToken)

            val response = api.login(LoginRequest(idToken))
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                TokenManager.clearToken()
                Result.failure(Exception("로그인 실패: ${response.code()} ${response.message()}"))
            }
        } catch (e: Exception) {
            TokenManager.clearToken()
            Result.failure(e)
        }
    }

    /**
     * 이메일 중복 확인
     */
    suspend fun checkEmailExists(email: String): Result<Boolean> {
        return try {
            val response = api.checkEmail(email)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.exists)
            } else {
                Result.failure(Exception("이메일 확인 실패"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 로그아웃
     */
    fun logout() {
        TokenManager.clearToken()
    }
}
