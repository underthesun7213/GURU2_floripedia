package com.example.plant

import com.google.firebase.appcheck.AppCheckProviderFactory
import com.google.firebase.appcheck.playintegrity.PlayIntegrityAppCheckProviderFactory

/**
 * 릴리즈 빌드용 App Check 공급자.
 * Play Integrity로 "정품 앱 + 정상 기기"에서 온 요청임을 증명한다.
 * (Play Console 연동 및 Firebase 콘솔 App Check 등록 필요)
 */
fun appCheckProviderFactory(): AppCheckProviderFactory =
    PlayIntegrityAppCheckProviderFactory.getInstance()
