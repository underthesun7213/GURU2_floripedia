package com.example.plant.data.remote

import com.example.plant.data.remote.api.AuthApi
import com.example.plant.data.remote.api.PlantApi
import com.example.plant.data.remote.api.UserApi
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {

    // TODO: 실제 서버 주소로 변경 [로컬/aws]
    private const val BASE_URL = "http://10.0.2.2:8000/api/v1/"

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .addInterceptor { chain ->
            val original = chain.request()
            val requestBuilder = original.newBuilder()

            // Multipart 요청이 아닐 때만 Content-Type 헤더 추가
            val contentType = original.body?.contentType()
            if (contentType == null || !contentType.toString().contains("multipart")) {
                requestBuilder.header("Content-Type", "application/json")
            }

            // Firebase Token이 있으면 Authorization 헤더에 추가
            TokenManager.getToken()?.let { token ->
                requestBuilder.header("Authorization", "Bearer $token")
            }

            chain.proceed(requestBuilder.build())
        }
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private val retrofit: Retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val authApi: AuthApi = retrofit.create(AuthApi::class.java)
    val plantApi: PlantApi = retrofit.create(PlantApi::class.java)
    val userApi: UserApi = retrofit.create(UserApi::class.java)
}

/**
 * Firebase ID Token 관리
 * SharedPreferences를 사용하여 앱 재시작 시에도 토큰 유지
 */
object TokenManager {
    private var idToken: String? = null
    private const val PREF_NAME = "floripedia_auth"
    private const val KEY_TOKEN = "id_token"

    /**
     * Application Context로 초기화 (Application onCreate에서 호출)
     */
    fun init(context: android.content.Context) {
        val prefs = context.getSharedPreferences(PREF_NAME, android.content.Context.MODE_PRIVATE)
        idToken = prefs.getString(KEY_TOKEN, null)
    }

    fun setToken(token: String?, context: android.content.Context? = null) {
        idToken = token
        context?.let {
            val prefs = it.getSharedPreferences(PREF_NAME, android.content.Context.MODE_PRIVATE)
            prefs.edit().putString(KEY_TOKEN, token).apply()
        }
    }

    fun getToken(): String? = idToken

    fun clearToken(context: android.content.Context? = null) {
        idToken = null
        context?.let {
            val prefs = it.getSharedPreferences(PREF_NAME, android.content.Context.MODE_PRIVATE)
            prefs.edit().remove(KEY_TOKEN).apply()
        }
    }
}
