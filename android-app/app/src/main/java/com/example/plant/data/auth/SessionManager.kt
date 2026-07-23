package com.example.plant.data.auth

import android.content.Context
import android.util.Log
import com.example.plant.data.remote.TokenManager
import com.example.plant.di.AppContainer
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/**
 * 익명 세션 관리자.
 *
 * 로그인 화면 없이 앱이 항상 유효한 Firebase 세션(익명 포함)을 갖도록 보장한다.
 * - 로그인돼 있지 않으면 Firebase 익명 로그인을 수행한다.
 * - ID Token을 저장하고, 백엔드에 유저 문서를 생성/조회한다(멱등).
 *
 * 여러 번 호출해도 안전하며, AI/찜/마이 기능이 항상 유효한 uid를 갖게 한다.
 * (익명 uid는 기기당 유지되며 재설치 시 초기화된다.)
 */
object SessionManager {

    private const val TAG = "SessionManager"

    // 앱 시작 시 Application·MainActivity가 동시 호출해도 익명 계정이 중복 생성되지 않도록 직렬화
    private val mutex = Mutex()

    suspend fun ensureSession(context: Context): Result<Unit> = mutex.withLock {
        try {
            val authManager = AppContainer.firebaseAuthManager

            // 1. 세션 없으면 익명 로그인 (mutex로 직렬화되어 최초 1회만 수행됨)
            if (!authManager.isLoggedIn()) {
                val signIn = authManager.signInAnonymously()
                if (signIn.isFailure) {
                    Log.w(TAG, "익명 로그인 실패", signIn.exceptionOrNull())
                    return@withLock Result.failure(
                        signIn.exceptionOrNull() ?: Exception("익명 로그인 실패")
                    )
                }
            }

            // 2. 토큰 확보 및 저장
            val token = authManager.getIdToken()
                ?: return@withLock Result.failure(Exception("ID Token 획득 실패"))
            TokenManager.setToken(token, context)

            // 3. 백엔드 유저 문서 보장 (기존 유저면 그대로 반환)
            AppContainer.authRepository.login(token)

            Result.success(Unit)
        } catch (e: Exception) {
            Log.e(TAG, "세션 보장 실패", e)
            Result.failure(e)
        }
    }
}
