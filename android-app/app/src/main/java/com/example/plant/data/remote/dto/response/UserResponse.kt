package com.example.plant.data.remote.dto.response

import com.google.gson.annotations.SerializedName

data class UserResponse(
    @SerializedName("_id")
    val id: String,

    @SerializedName("email")
    val email: String,

    @SerializedName("nickname")
    val nickname: String,

    @SerializedName("profileImageUrl")
    val profileImageUrl: String?,

    @SerializedName("favoritePlantIds")
    val favoritePlantIds: List<String>,

    @SerializedName("createdAt")
    val createdAt: String
)

data class FavoriteToggleResponse(
    @SerializedName("isFavorite")
    val isFavorite: Boolean,

    @SerializedName("message")
    val message: String
)

data class FavoriteCountResponse(
    @SerializedName("count")
    val count: Int
)

data class MessageResponse(
    @SerializedName("message")
    val message: String
)
