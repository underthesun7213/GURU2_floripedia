package com.example.plant.data.remote.dto.request

import com.google.gson.annotations.SerializedName

data class UserUpdateRequest(
    @SerializedName("nickname")
    val nickname: String? = null,

    @SerializedName("profileImageUrl")
    val profileImageUrl: String? = null
)
