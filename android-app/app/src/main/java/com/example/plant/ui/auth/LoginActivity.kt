package com.example.plant.ui.auth

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.plant.data.remote.TokenManager
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
                binding.etEmail.error = "이메일을 입력해주세요"
                return@setOnClickListener
            }
            if (!com.example.plant.util.InputValidator.isValidEmail(email)) {
                binding.etEmail.error = "올바른 이메일 형식을 입력해주세요"
                return@setOnClickListener
            }
            sendPasswordResetEmail(email)
        }
    }

    private fun validateInput(email: String, password: String): Boolean {
        if (email.isEmpty()) {
            binding.etEmail.error = "이메일을 입력해주세요"
            return false
        }
        if (!com.example.plant.util.InputValidator.isValidEmail(email)) {
            binding.etEmail.error = "올바른 이메일 형식을 입력해주세요"
            return false
        }
        if (password.isEmpty()) {
            binding.etPassword.error = "비밀번호를 입력해주세요"
            return false
        }
        if (!com.example.plant.util.InputValidator.isValidPassword(password)) {
            binding.etPassword.error = "비밀번호는 6자 이상이어야 합니다"
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
        val result = AppContainer.authRepository.login(idToken)

        result.onSuccess { user ->
            Log.d("LoginActivity", "백엔드 로그인 성공: ${user.nickname}")
            TokenManager.setToken(idToken, applicationContext)
            navigateToMain()
        }.onFailure { error ->
            Log.e("LoginActivity", "백엔드 로그인 실패", error)
            // 백엔드 실패해도 Firebase 로그인은 성공했으므로 토큰 저장 후 메인으로 이동
            TokenManager.setToken(idToken, applicationContext)
            navigateToMain()
        }
    }

    private fun sendPasswordResetEmail(email: String) {
        lifecycleScope.launch {
            val result = AppContainer.firebaseAuthManager.sendPasswordResetEmail(email)
            result.onSuccess {
                // Toast 대신 AlertDialog를 띄워 사용자에게 명확하게 알림
                androidx.appcompat.app.AlertDialog.Builder(this@LoginActivity)
                    .setTitle("이메일 전송 완료")
                    .setMessage("입력하신 이메일($email)로 비밀번호 재설정 링크를 보냈습니다. 이메일을 확인해 주세요.")
                    .setPositiveButton("확인", null)
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
