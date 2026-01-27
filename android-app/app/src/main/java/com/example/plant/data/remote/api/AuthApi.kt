package com.example.plant.data.remote.api

import com.example.plant.data.remote.dto.request.LoginRequest
import com.example.plant.data.remote.dto.response.EmailCheckResponse
import com.example.plant.data.remote.dto.response.UserResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface AuthApi {

    /**
     * Firebase ID Token 기반 로그인/자동 회원가입
     */
    @POST("auth/login")
    suspend fun login(
        @Body request: LoginRequest
    ): Response<UserResponse>

    /**
     * 이메일 중복 확인
     */
    @GET("auth/check-email")
    suspend fun checkEmail(
        @Query("email") email: String
    ): Response<EmailCheckResponse>
}
