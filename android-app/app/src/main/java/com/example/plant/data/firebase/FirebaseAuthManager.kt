package com.example.plant.data.firebase

import com.google.firebase.auth.EmailAuthProvider
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseUser
import kotlinx.coroutines.tasks.await

/**
 * Firebase Authentication 관리 클래스 (이메일/비밀번호 로그인)
 */
class FirebaseAuthManager {

    private val auth: FirebaseAuth = FirebaseAuth.getInstance()

    /**
     * 회원가입 (이메일/비밀번호)
     */
    suspend fun signUp(email: String, password: String): Result<FirebaseUser> {
        return try {
            val result = auth.createUserWithEmailAndPassword(email, password).await()
            result.user?.let {
                Result.success(it)
            } ?: Result.failure(Exception("회원가입 실패"))
        } catch (e: Exception) {
            Result.failure(Exception(getErrorMessage(e)))
        }
    }

    /**
     * 로그인 (이메일/비밀번호)
     */
    suspend fun signIn(email: String, password: String): Result<FirebaseUser> {
        return try {
            val result = auth.signInWithEmailAndPassword(email, password).await()
            result.user?.let {
                Result.success(it)
            } ?: Result.failure(Exception("로그인 실패"))
        } catch (e: Exception) {
            Result.failure(Exception(getErrorMessage(e)))
        }
    }

    /**
     * 현재 로그인된 사용자의 ID Token 가져오기
     */
    suspend fun getIdToken(): String? {
        return try {
            auth.currentUser?.getIdToken(false)?.await()?.token
        } catch (e: Exception) {
            null
        }
    }

    /**
     * 현재 로그인된 사용자
     */
    fun getCurrentUser(): FirebaseUser? = auth.currentUser

    /**
     * 로그인 상태 확인
     */
    fun isLoggedIn(): Boolean = auth.currentUser != null

    /**
     * 로그아웃
     */
    fun signOut() {
        auth.signOut()
    }

    /**
     * 회원 탈퇴
     */
    suspend fun deleteAccount(): Result<Unit> {
        return try {
            auth.currentUser?.delete()?.await()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * 비밀번호 재설정 이메일 전송
     */
    suspend fun sendPasswordResetEmail(email: String): Result<Unit> {
        return try {
            auth.sendPasswordResetEmail(email).await()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(Exception(getErrorMessage(e)))
        }
    }

    /**
     * 비밀번호 직접 변경 (마이페이지에서 사용)
     * 보안상 현재 비밀번호로 재인증 후 새 비밀번호로 변경
     *
     * @param currentPassword 현재 비밀번호 (재인증용)
     * @param newPassword 새 비밀번호
     */
    suspend fun changePassword(currentPassword: String, newPassword: String): Result<Unit> {
        return try {
            val user = auth.currentUser
                ?: return Result.failure(Exception("로그인이 필요합니다"))

            val email = user.email
                ?: return Result.failure(Exception("이메일 정보를 찾을 수 없습니다"))

            // 1. 현재 비밀번호로 재인증 (보안상 필수)
            val credential = EmailAuthProvider.getCredential(email, currentPassword)
            user.reauthenticate(credential).await()

            // 2. 새 비밀번호로 변경
            user.updatePassword(newPassword).await()

            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(Exception(getErrorMessage(e)))
        }
    }

    private fun getErrorMessage(e: Exception): String {
        return when {
            e.message?.contains("email address is badly formatted") == true -> "이메일 형식이 올바르지 않습니다"
            e.message?.contains("password is invalid") == true -> "비밀번호가 올바르지 않습니다"
            e.message?.contains("no user record") == true -> "등록되지 않은 이메일입니다"
            e.message?.contains("email address is already in use") == true -> "이미 사용중인 이메일입니다"
            e.message?.contains("password should be at least 6") == true -> "비밀번호는 6자 이상이어야 합니다"
            else -> e.message ?: "알 수 없는 오류가 발생했습니다"
        }
    }
}
