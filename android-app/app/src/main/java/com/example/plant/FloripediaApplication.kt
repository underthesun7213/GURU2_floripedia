package com.example.plant

import android.app.Application
import com.example.plant.data.remote.TokenManager
import com.google.android.gms.ads.MobileAds

class FloripediaApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        TokenManager.init(this)
        MobileAds.initialize(this)
    }
}
