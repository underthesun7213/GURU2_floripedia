package com.example.plant

import com.google.firebase.appcheck.AppCheckProviderFactory
import com.google.firebase.appcheck.debug.DebugAppCheckProviderFactory

/**
 * 디버그 빌드용 App Check 공급자.
 * 최초 실행 시 logcat에 디버그 시크릿이 출력되며,
 * 이를 Firebase 콘솔 > App Check > 앱 > 디버그 토큰 관리에 등록해야 검증이 통과한다.
 */
fun appCheckProviderFactory(): AppCheckProviderFactory =
    DebugAppCheckProviderFactory.getInstance()
