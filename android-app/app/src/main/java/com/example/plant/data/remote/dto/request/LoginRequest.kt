package com.example.plant.data.remote.dto.request

import com.google.gson.annotations.SerializedName

data class LoginRequest(
    @SerializedName("idToken")
    val idToken: String,
    // 신규 가입 시 동의 캡처용 (기존 유저 로그인 시 백엔드가 무시)
    @SerializedName("termsAgreed")
    val termsAgreed: Boolean = false,
    @SerializedName("privacyAgreed")
    val privacyAgreed: Boolean = false
)
