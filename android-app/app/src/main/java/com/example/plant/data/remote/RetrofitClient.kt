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

    private const val BASE_URL = "http://10.0.2.2:8000/"
    
    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    // 일반 API용 클라이언트 (30초)
    private val commonHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .addInterceptor { chain ->
            val original = chain.request()
            val requestBuilder = original.newBuilder()
            val contentType = original.body?.contentType()
            if (contentType == null || !contentType.toString().contains("multipart")) {
                requestBuilder.header("Content-Type", "application/json")
            }
            TokenManager.getToken()?.let { token ->
                requestBuilder.header("Authorization", "Bearer $token")
            }
            chain.proceed(requestBuilder.build())
        }
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    // 이미지 검색/추천 등 오래 걸리는 작업용 클라이언트 (5분)
    private val longTimeoutHttpClient = commonHttpClient.newBuilder()
        .connectTimeout(5, TimeUnit.MINUTES)
        .readTimeout(5, TimeUnit.MINUTES)
        .writeTimeout(5, TimeUnit.MINUTES)
        .build()

    private val commonRetrofit: Retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(commonHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    private val longTimeoutRetrofit: Retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(longTimeoutHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val authApi: AuthApi = commonRetrofit.create(AuthApi::class.java)
    val userApi: UserApi = commonRetrofit.create(UserApi::class.java)
    
    // 식물 관련 API(이미지 검색 포함)는 5분 타임아웃 적용
    val plantApi: PlantApi = longTimeoutRetrofit.create(PlantApi::class.java)
}

object TokenManager {
    private var idToken: String? = null
    private const val PREF_NAME = "floripedia_auth"
    private const val KEY_TOKEN = "id_token"

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
