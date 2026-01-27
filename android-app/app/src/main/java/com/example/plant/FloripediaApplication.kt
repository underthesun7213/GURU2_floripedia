package com.example.plant

import android.app.Application
import com.example.plant.data.remote.TokenManager

class FloripediaApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        // 토큰 매니저 초기화 (저장된 토큰 로드)
        TokenManager.init(this)
    }
}
