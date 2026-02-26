package com.example.plant.util

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.util.Log
import android.widget.Toast
import com.example.plant.di.AppContainer
import com.example.plant.ui.auth.LoginActivity
import java.net.UnknownHostException
import java.net.SocketTimeoutException
import java.io.IOException

/**
 * 통합 에러 처리 유틸리티
 */
object ErrorHandler {

    // 중복 Toast 방지용 (마지막 에러 메시지 + 시간)
    private var lastErrorMessage: String? = null
    private var lastErrorTime: Long = 0
    private const val ERROR_DEBOUNCE_MS = 5000L  // 5초 내 동일 메시지 무시

    /**
     * 네트워크 연결 상태 확인
     */
    fun isNetworkAvailable(context: Context): Boolean {
        val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = connectivityManager.activeNetwork ?: return false
        val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
               capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
    }

    /**
     * 인증 에러인지 확인
     */
    fun isAuthError(error: Throwable): Boolean {
        val message = error.message ?: return false
        return message.contains("401") || message.contains("403") ||
               message.contains("Unauthorized") || message.contains("인증")
    }

    /**
     * 에러를 사용자 친화적인 메시지로 변환
     */
    fun getErrorMessage(error: Throwable): String {
        return when (error) {
            is UnknownHostException -> "인터넷 연결을 확인해주세요"
            is SocketTimeoutException -> "요청 시간이 초과되었습니다. 다시 시도해주세요"
            is IOException -> "네트워크 오류가 발생했습니다. 연결을 확인해주세요"
            else -> {
                val message = error.message ?: "알 수 없는 오류가 발생했습니다"
                // HTTP 에러 코드가 포함된 경우 처리
                if (message.contains("404")) {
                    "요청한 정보를 찾을 수 없습니다"
                } else if (message.contains("401") || message.contains("403")) {
                    "로그인이 필요합니다"
                } else if (message.contains("500")) {
                    "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요"
                } else {
                    message
                }
            }
        }
    }

    /**
     * 에러 처리 및 사용자에게 메시지 표시
     * 동일한 메시지가 5초 내 반복되면 무시 (중복 Toast 방지)
     */
    fun handleError(context: Context, error: Throwable, tag: String, defaultMessage: String = "오류가 발생했습니다") {
        Log.e(tag, "에러 발생: ${error.message}", error)

        val message = if (isNetworkAvailable(context)) {
            getErrorMessage(error)
        } else {
            "인터넷 연결을 확인해주세요"
        }

        // 중복 Toast 방지: 동일 메시지가 5초 내 반복되면 무시
        val now = System.currentTimeMillis()
        if (message == lastErrorMessage && (now - lastErrorTime) < ERROR_DEBOUNCE_MS) {
            Log.d(tag, "중복 에러 메시지 무시 (${(now - lastErrorTime)}ms 전 표시됨): $message")
            return
        }

        Log.w(tag, "에러 Toast 표시: $message (from: $tag)")
        lastErrorMessage = message
        lastErrorTime = now

        Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
    }

    /**
     * 네트워크 연결 확인 및 에러 처리
     */
    fun handleApiError(context: Context, error: Throwable, tag: String): Boolean {
        // 네트워크 연결 확인
        if (!isNetworkAvailable(context)) {
            Toast.makeText(context, "인터넷 연결을 확인해주세요", Toast.LENGTH_SHORT).show()
            return true // 네트워크 에러 처리 완료
        }

        // 일반 에러 처리
        handleError(context, error, tag)
        return true
    }

    /**
     * 인증이 필요한 API 에러 처리 (401/403 시 로그인 화면으로 리다이렉트)
     */
    fun handleAuthRequiredError(activity: Activity, error: Throwable, tag: String): Boolean {
        Log.e(tag, "에러 발생", error)

        // 네트워크 연결 확인
        if (!isNetworkAvailable(activity)) {
            Toast.makeText(activity, "인터넷 연결을 확인해주세요", Toast.LENGTH_SHORT).show()
            return true
        }

        // 인증 에러인 경우 로그인 화면으로 리다이렉트
        if (isAuthError(error)) {
            redirectToLogin(activity)
            return true
        }

        // 일반 에러 처리
        handleError(activity, error, tag)
        return true
    }

    /**
     * 로그인 화면으로 리다이렉트
     */
    fun redirectToLogin(activity: Activity) {
        // Firebase 로그아웃
        AppContainer.firebaseAuthManager.signOut()

        Toast.makeText(activity, "로그인이 필요합니다", Toast.LENGTH_SHORT).show()

        val intent = Intent(activity, LoginActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        activity.startActivity(intent)
        activity.finish()
    }
}
