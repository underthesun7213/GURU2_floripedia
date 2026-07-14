# ==========================================================
# Floripedia R8/ProGuard keep 규칙
# minifyEnabled=true 시 리플렉션 기반 코드(Gson DTO 등)가 제거·난독화되지 않도록 보존.
# ==========================================================

# --- Gson: 어노테이션/제네릭 시그니처 보존 ---
-keepattributes Signature
-keepattributes *Annotation*
-keepattributes RuntimeVisibleAnnotations
-keepattributes RuntimeVisibleParameterAnnotations
-keep class com.google.gson.reflect.TypeToken { *; }
-keep class * extends com.google.gson.reflect.TypeToken

# --- 네트워크 DTO(요청/응답): Gson이 리플렉션으로 매핑하므로 필드/클래스 보존 ---
-keep class com.example.plant.data.remote.dto.** { *; }
-keepclassmembers class com.example.plant.data.remote.dto.** { <fields>; }

# --- 로컬 Gson 직렬화 모델 (SharedPreferences) ---
-keep class com.example.plant.util.RecentPlantManager$RecentPlant { *; }

# @SerializedName 붙은 필드는 이름 유지
-keepclassmembers,allowobfuscation class * {
    @com.google.gson.annotations.SerializedName <fields>;
}

# --- Retrofit ---
-keepattributes InnerClasses, EnclosingMethod
-keep interface com.example.plant.data.remote.api.** { *; }
-keep,allowobfuscation,allowshrinking interface retrofit2.Call
-keep,allowobfuscation,allowshrinking class retrofit2.Response
-keep,allowobfuscation,allowshrinking class kotlin.coroutines.Continuation

# --- 코루틴 ---
-keepclassmembers class kotlinx.coroutines.** { *; }

# Retrofit·OkHttp·Firebase·Coil·play-services는 각 라이브러리가 consumer proguard 규칙을
# 번들로 제공하므로 별도 keep 없이도 동작한다. 문제 발생 시 여기에 추가.
