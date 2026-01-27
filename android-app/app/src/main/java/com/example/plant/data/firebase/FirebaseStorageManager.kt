package com.example.plant.data.firebase

import android.net.Uri
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.storage.FirebaseStorage
import kotlinx.coroutines.tasks.await
import java.util.UUID

/**
 * Firebase Storage 관리 클래스
 */
class FirebaseStorageManager {

    private val storage = FirebaseStorage.getInstance()
    private val auth = FirebaseAuth.getInstance()

    /**
     * 프로필 이미지 업로드
     * @param imageUri 업로드할 이미지 Uri
     * @return 업로드된 이미지의 다운로드 URL
     */
    suspend fun uploadProfileImage(imageUri: Uri): Result<String> {
        return try {
            val userId = auth.currentUser?.uid
                ?: return Result.failure(Exception("로그인이 필요합니다"))

            val fileName = "profile_${userId}_${System.currentTimeMillis()}.jpg"
            val ref = storage.reference.child("profile_images/$fileName")

            // 업로드
            ref.putFile(imageUri).await()

            // 다운로드 URL 가져오기
            val downloadUrl = ref.downloadUrl.await().toString()
            Result.success(downloadUrl)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 바이트 배열로 프로필 이미지 업로드
     */
    suspend fun uploadProfileImage(imageData: ByteArray): Result<String> {
        return try {
            val userId = auth.currentUser?.uid
                ?: return Result.failure(Exception("로그인이 필요합니다"))

            val fileName = "profile_${userId}_${System.currentTimeMillis()}.jpg"
            val ref = storage.reference.child("profile_images/$fileName")

            // 업로드
            ref.putBytes(imageData).await()

            // 다운로드 URL 가져오기
            val downloadUrl = ref.downloadUrl.await().toString()
            Result.success(downloadUrl)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 식물 검색용 이미지 업로드 (임시)
     */
    suspend fun uploadSearchImage(imageData: ByteArray): Result<String> {
        return try {
            val fileName = "search_${UUID.randomUUID()}.jpg"
            val ref = storage.reference.child("search_images/$fileName")

            ref.putBytes(imageData).await()
            val downloadUrl = ref.downloadUrl.await().toString()
            Result.success(downloadUrl)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 이미지 삭제
     */
    suspend fun deleteImage(imageUrl: String): Result<Unit> {
        return try {
            val ref = storage.getReferenceFromUrl(imageUrl)
            ref.delete().await()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
