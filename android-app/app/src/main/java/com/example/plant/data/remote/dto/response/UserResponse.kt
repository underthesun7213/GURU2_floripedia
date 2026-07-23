package com.example.plant.data.remote.dto.response

import com.google.gson.annotations.SerializedName

data class LevelInfo(
    @SerializedName("level")
    val level: Int,

    @SerializedName("title")
    val title: String,

    @SerializedName("totalExp")
    val totalExp: Int,

    @SerializedName("currentLevelExp")
    val currentLevelExp: Int,

    @SerializedName("nextLevelExp")
    val nextLevelExp: Int,

    @SerializedName("discoveredPlantCount")
    val discoveredPlantCount: Int
)

data class UserResponse(
    @SerializedName("_id")
    val id: String,

    @SerializedName("email")
    val email: String? = null,  // 익명 세션은 email이 없음

    @SerializedName("nickname")
    val nickname: String,

    @SerializedName("profileImageUrl")
    val profileImageUrl: String?,

    @SerializedName("favoritePlantIds")
    val favoritePlantIds: List<String>,

    @SerializedName("createdAt")
    val createdAt: String,

    @SerializedName("levelInfo")
    val levelInfo: LevelInfo?,

    @SerializedName("discoveredPlantIds")
    val discoveredPlantIds: List<String> = emptyList()
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
