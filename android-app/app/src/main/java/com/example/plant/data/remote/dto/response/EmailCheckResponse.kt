package com.example.plant.data.remote.dto.response

import com.google.gson.annotations.SerializedName

/**
 * 이메일 중복 확인 응답
 */
data class EmailCheckResponse(
    @SerializedName("exists") val exists: Boolean
)
