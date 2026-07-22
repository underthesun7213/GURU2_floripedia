package com.example.plant

import android.app.Application
import com.example.plant.data.auth.SessionManager
import com.example.plant.data.remote.TokenManager
import com.google.android.gms.ads.MobileAds
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class FloripediaApplication : Application() {
    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreate() {
        super.onCreate()
        TokenManager.init(this)
        MobileAds.initialize(this)
        // 익명 세션 워밍업: 첫 실행부터 유효한 uid/토큰을 갖도록 백그라운드로 보장
        appScope.launch {
            SessionManager.ensureSession(this@FloripediaApplication)
        }
    }
}
