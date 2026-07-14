package com.example.plant.ui.auth

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.plant.data.remote.TokenManager
import com.example.plant.R
import com.example.plant.databinding.ActivityLoginBinding
import com.example.plant.di.AppContainer
import com.example.plant.ui.home.MainActivity
import kotlinx.coroutines.launch

/**
 * 로그인 화면
 * 흐름: 로그인 → 메인1
 */
class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // 이미 로그인되어 있으면 메인으로 이동
        if (AppContainer.firebaseAuthManager.isLoggedIn()) {
            navigateToMain()
            return
        }

        setupUI()
    }

    private fun setupUI() {
        // 뒤로가기 버튼 → 메인으로 이동
        binding.btnBack.setOnClickListener {
            navigateToMain()
        }

        // 로그인 버튼
        binding.btnLogin.setOnClickListener {
            val email = binding.etEmail.text.toString().trim()
            val password = binding.etPassword.text.toString().trim()

            if (validateInput(email, password)) {
                performLogin(email, password)
            }
        }

        // 회원가입 텍스트 클릭 → 회원가입 화면으로
        binding.tvSignUp.setOnClickListener {
            val intent = Intent(this, SignUpActivity::class.java)
            startActivity(intent)
        }

        // 비밀번호 찾기
        binding.tvForgotPassword.setOnClickListener {
            val email = binding.etEmail.text.toString().trim()
            if (!com.example.plant.util.InputValidator.isNotEmpty(email)) {
                binding.etEmail.error = getString(R.string.error_email_required)
                return@setOnClickListener
            }
            if (!com.example.plant.util.InputValidator.isValidEmail(email)) {
                binding.etEmail.error = getString(R.string.error_email_invalid)
                return@setOnClickListener
            }
            sendPasswordResetEmail(email)
        }
    }

    private fun validateInput(email: String, password: String): Boolean {
        if (email.isEmpty()) {
            binding.etEmail.error = getString(R.string.error_email_required)
            return false
        }
        if (!com.example.plant.util.InputValidator.isValidEmail(email)) {
            binding.etEmail.error = getString(R.string.error_email_invalid)
            return false
        }
        if (password.isEmpty()) {
            binding.etPassword.error = getString(R.string.error_password_required)
            return false
        }
        if (!com.example.plant.util.InputValidator.isValidPassword(password)) {
            binding.etPassword.error = getString(R.string.error_password_too_short)
            return false
        }
        return true
    }

    private fun performLogin(email: String, password: String) {
        binding.btnLogin.isEnabled = false

        lifecycleScope.launch {
            // Firebase 로그인
            val result = AppContainer.firebaseAuthManager.signIn(email, password)

            result.onSuccess { firebaseUser ->
                Log.d("LoginActivity", "Firebase 로그인 성공: ${firebaseUser.email}")

                // ID Token 가져와서 백엔드에 전송
                val idToken = AppContainer.firebaseAuthManager.getIdToken()
                if (idToken != null) {
                    loginToBackend(idToken)
                } else {
                    navigateToMain()
                }
            }.onFailure { error ->
                com.example.plant.util.ErrorHandler.handleApiError(
                    this@LoginActivity,
                    error,
                    "LoginActivity"
                )
                binding.btnLogin.isEnabled = true
            }
        }
    }

    private suspend fun loginToBackend(idToken: String) {
        // 1회 재시도 (일시적 백엔드 장애 대응)
        var result = AppContainer.authRepository.login(idToken)
        if (result.isFailure) {
            Log.w("LoginActivity", "백엔드 로그인 실패, 1회 재시도")
            result = AppContainer.authRepository.login(idToken)
        }

        result.onSuccess { user ->
            Log.d("LoginActivity", "백엔드 로그인 성공: ${user.nickname}")
            TokenManager.setToken(idToken, applicationContext)
            navigateToMain()
        }.onFailure { error ->
            Log.e("LoginActivity", "백엔드 로그인 최종 실패", error)
            // 반쪽 로그인 상태(Firebase O, 서버 X) 방지: 세션 해제 후 로그인 화면 유지
            AppContainer.firebaseAuthManager.signOut()
            TokenManager.clearToken(applicationContext)
            Toast.makeText(
                this@LoginActivity,
                getString(R.string.error_login_backend_failed),
                Toast.LENGTH_LONG
            ).show()
            binding.btnLogin.isEnabled = true
        }
    }

    private fun sendPasswordResetEmail(email: String) {
        lifecycleScope.launch {
            val result = AppContainer.firebaseAuthManager.sendPasswordResetEmail(email)
            result.onSuccess {
                // Toast 대신 AlertDialog를 띄워 사용자에게 명확하게 알림
                androidx.appcompat.app.AlertDialog.Builder(this@LoginActivity)
                    .setTitle(getString(R.string.email_sent_title))
                    .setMessage(getString(R.string.email_sent_message, email))
                    .setPositiveButton(getString(R.string.confirm), null)
                    .show()
            }.onFailure { error ->
                com.example.plant.util.ErrorHandler.handleApiError(
                    this@LoginActivity,
                    error,
                    "LoginActivity"
                )
            }
        }
    }

    private fun navigateToMain() {
        val intent = Intent(this, MainActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }
}
