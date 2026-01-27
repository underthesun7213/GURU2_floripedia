package com.example.plant.data.remote.dto.request

import com.google.gson.annotations.SerializedName

data class LoginRequest(
    @SerializedName("idToken")
    val idToken: String
)
