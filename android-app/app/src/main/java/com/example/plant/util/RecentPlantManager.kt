package com.example.plant.util

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

/**
 * 최근 본 식물 관리 유틸리티
 * 최대 4개까지 저장하며, 최신순으로 유지
 */
object RecentPlantManager {
    private const val PREFS_NAME = "recent_plants_prefs"
    private const val KEY_RECENT_PLANTS = "recent_plants"
    private const val MAX_RECENT_PLANTS = 16

    private fun getSharedPreferences(context: Context): SharedPreferences {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }

    /**
     * 최근 본 식물 추가
     */
    fun addRecentPlant(
        context: Context,
        plantId: String,
        plantName: String,
        imageUrl: String? = null,
        description: String? = null
    ) {
        val prefs = getSharedPreferences(context)
        val recentPlants = getRecentPlants(context).toMutableList()

        // 이미 존재하는 경우 제거 (중복 방지)
        recentPlants.removeAll { it.id == plantId }

        // 맨 앞에 추가 (최신순)
        recentPlants.add(0, RecentPlant(plantId, plantName, imageUrl, description))

        // 최대 개수 제한
        if (recentPlants.size > MAX_RECENT_PLANTS) {
            recentPlants.removeAt(recentPlants.size - 1)
        }

        // 저장
        val gson = Gson()
        val json = gson.toJson(recentPlants)
        prefs.edit().putString(KEY_RECENT_PLANTS, json).apply()
    }

    /**
     * 최근 본 식물 목록 조회 (최대 4개)
     */
    fun getRecentPlants(context: Context): List<RecentPlant> {
        val prefs = getSharedPreferences(context)
        val json = prefs.getString(KEY_RECENT_PLANTS, null) ?: return emptyList()

        return try {
            val gson = Gson()
            val type = object : TypeToken<List<RecentPlant>>() {}.type
            gson.fromJson<List<RecentPlant>>(json, type) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    /**
     * 최근 본 식물 목록 초기화
     */
    fun clearRecentPlants(context: Context) {
        val prefs = getSharedPreferences(context)
        prefs.edit().remove(KEY_RECENT_PLANTS).apply()
    }

    /**
     * 최근 본 식물 데이터 클래스
     */
    data class RecentPlant(
        val id: String,
        val name: String,
        val imageUrl: String? = null,
        val description: String? = null
    )
}
