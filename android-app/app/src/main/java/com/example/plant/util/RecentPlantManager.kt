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
    private const val KEY_CACHE_VERSION = "cache_version"
    private const val MAX_RECENT_PLANTS = 16

    // 캐시 스키마 버전. 저장된 description 스냅샷 형식이 바뀌면 올린다.
    // v2(2026-07): 설명 소스를 이다체 preContent → 습니다체 seasonDescription 으로 전환.
    //   → 이전 버전의 이다체 스냅샷을 1회 무효화(clear)해 새로 습니다체로 다시 쌓이게 한다.
    private const val CURRENT_CACHE_VERSION = 2

    private fun getSharedPreferences(context: Context): SharedPreferences {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    }

    /**
     * 캐시 버전이 낮으면(구 스냅샷) 최근 목록을 비우고 버전을 올린다. (구 이다체 설명 무효화)
     * @return 유효한 캐시면 true, 무효화되어 비워졌으면 false
     */
    private fun ensureCacheVersion(prefs: SharedPreferences): Boolean {
        if (prefs.getInt(KEY_CACHE_VERSION, 1) < CURRENT_CACHE_VERSION) {
            prefs.edit()
                .remove(KEY_RECENT_PLANTS)
                .putInt(KEY_CACHE_VERSION, CURRENT_CACHE_VERSION)
                .apply()
            return false
        }
        return true
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
        if (!ensureCacheVersion(prefs)) return emptyList()   // 구 이다체 스냅샷 무효화
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
     * 최근 본 식물에서 특정 식물 제거.
     * (예: 상세 조회가 404 → 카탈로그에서 삭제된 식물을 로컬 최근 목록에서도 정리)
     */
    fun removeRecentPlant(context: Context, plantId: String) {
        val prefs = getSharedPreferences(context)
        val recentPlants = getRecentPlants(context).toMutableList()
        val changed = recentPlants.removeAll { it.id == plantId }
        if (changed) {
            val json = Gson().toJson(recentPlants)
            prefs.edit().putString(KEY_RECENT_PLANTS, json).apply()
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
