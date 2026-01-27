package com.example.plant.ui.auth

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.ColorStateList
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.util.Log
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.example.plant.R
import com.example.plant.data.remote.TokenManager
import com.example.plant.databinding.ActivitySignupBinding
import com.example.plant.di.AppContainer
import kotlinx.coroutines.launch

/**
 * 회원가입 화면 (첫 화면)
 * 흐름: 회원가입 → 로그인
 */
class SignUpActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySignupBinding
    private var selectedImageUri: Uri? = null

    // 갤러리에서 사진 선택
    private val pickImageLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let {
            selectedImageUri = it
            binding.ivProfileSelect.setImageURI(it)
        }
    }

    // 권한 요청
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            openGallery()
        } else {
            Toast.makeText(this, "갤러리 접근 권한이 필요합니다.", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySignupBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // 이미 로그인되어 있으면 메인으로 이동
        if (AppContainer.firebaseAuthManager.isLoggedIn()) {
            navigateToLogin()
            return
        }

        setupUI()
        setupTextWatchers()
    }

    private fun setupUI() {
        // 프로필 이미지 선택
        binding.btnProfileAdd.setOnClickListener {
            checkPermissionAndOpenGallery()
        }

        // 중복 확인 버튼 (이메일)
        binding.btnCheckId.setOnClickListener {
            val email = binding.etId.text.toString().trim()
            if (email.isEmpty()) {
                binding.etId.error = "이메일을 입력해주세요"
                return@setOnClickListener
            }
            if (!com.example.plant.util.InputValidator.isValidEmail(email)) {
                binding.etId.error = "올바른 이메일 형식을 입력해주세요"
                return@setOnClickListener
            }
            checkEmailExists(email)
        }

        // 가입하기 버튼
        binding.btnSignUp.setOnClickListener {
            performSignUp()
        }

        // 로그인 화면으로 이동
        binding.tvLogin.setOnClickListener {
            navigateToLogin()
        }

        // 뒤로가기 버튼
        binding.btnBack.setOnClickListener {
            navigateToLogin()
        }
    }

    private fun performSignUp() {
        val nickname = binding.etNickname.text.toString().trim()
        val email = binding.etId.text.toString().trim()
        val password = binding.etPw.text.toString().trim()
        val passwordCheck = binding.etPwCheck.text.toString().trim()

        // 유효성 검사
        if (!validateInput(nickname, email, password, passwordCheck)) {
            return
        }

        binding.btnSignUp.isEnabled = false

        lifecycleScope.launch {
            // Firebase 회원가입
            val result = AppContainer.firebaseAuthManager.signUp(email, password)

            result.onSuccess { firebaseUser ->
                Log.d("SignUpActivity", "Firebase 회원가입 성공: ${firebaseUser.email}")

                // 프로필 이미지 업로드
                selectedImageUri?.let { uri ->
                    uploadProfileImage(uri)
                }

                // 백엔드에 사용자 등록
                val idToken = AppContainer.firebaseAuthManager.getIdToken()
                if (idToken != null) {
                    registerToBackend(idToken, nickname)
                } else {
                    showSuccessAndNavigate()
                }
            }.onFailure { error ->
                com.example.plant.util.ErrorHandler.handleApiError(
                    this@SignUpActivity,
                    error,
                    "SignUpActivity"
                )
                binding.btnSignUp.isEnabled = true
            }
        }
    }

    private fun validateInput(nickname: String, email: String, password: String, passwordCheck: String): Boolean {
        if (nickname.isEmpty()) {
            binding.etNickname.error = "닉네임을 입력해주세요"
            return false
        }
        if (!com.example.plant.util.InputValidator.isValidNickname(nickname)) {
            binding.etNickname.error = "닉네임은 1-20자이며, 한글/영문/숫자만 사용 가능합니다"
            return false
        }
        if (email.isEmpty()) {
            binding.etId.error = "이메일을 입력해주세요"
            return false
        }
        if (!com.example.plant.util.InputValidator.isValidEmail(email)) {
            binding.etId.error = "올바른 이메일 형식을 입력해주세요"
            return false
        }
        if (password.isEmpty()) {
            binding.etPw.error = "비밀번호를 입력해주세요"
            return false
        }
        if (!com.example.plant.util.InputValidator.isValidPassword(password)) {
            binding.etPw.error = "비밀번호는 6자 이상이어야 합니다"
            return false
        }
        if (password != passwordCheck) {
            binding.etPwCheck.error = "비밀번호가 일치하지 않습니다"
            return false
        }
        return true
    }

    private suspend fun uploadProfileImage(uri: Uri) {
        val result = AppContainer.firebaseStorageManager.uploadProfileImage(uri)
        result.onSuccess { url ->
            Log.d("SignUpActivity", "프로필 이미지 업로드 성공: $url")
            // 백엔드에 프로필 URL 업데이트
            AppContainer.userRepository.updateProfile(nickname = null, profileImageUrl = url)
        }.onFailure { error ->
            Log.e("SignUpActivity", "이미지 업로드 실패", error)
        }
    }

    private suspend fun registerToBackend(idToken: String, nickname: String) {
        val result = AppContainer.authRepository.login(idToken)

        result.onSuccess { user ->
            Log.d("SignUpActivity", "백엔드 등록 성공")
            TokenManager.setToken(idToken, applicationContext)

            // 닉네임 업데이트
            AppContainer.userRepository.updateProfile(nickname = nickname, profileImageUrl = null)

            showSuccessAndNavigate()
        }.onFailure { error ->
            Log.e("SignUpActivity", "백엔드 등록 실패", error)
            showSuccessAndNavigate()
        }
    }

    private fun showSuccessAndNavigate() {
        Toast.makeText(this, "회원가입이 완료되었습니다", Toast.LENGTH_SHORT).show()
        // 로그아웃 후 로그인 화면으로 (로그인 흐름 유지)
        AppContainer.firebaseAuthManager.signOut()
        navigateToLogin()
    }

    private fun navigateToLogin() {
        val intent = Intent(this, LoginActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }

    private fun checkPermissionAndOpenGallery() {
        val permission = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            Manifest.permission.READ_MEDIA_IMAGES
        } else {
            Manifest.permission.READ_EXTERNAL_STORAGE
        }

        when {
            ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED -> {
                openGallery()
            }
            else -> {
                requestPermissionLauncher.launch(permission)
            }
        }
    }

    private fun openGallery() {
        pickImageLauncher.launch("image/*")
    }

    private fun setupTextWatchers() {
        val watcher = object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                updateButtonStates()
            }
            override fun afterTextChanged(s: Editable?) {}
        }

        binding.etNickname.addTextChangedListener(watcher)
        binding.etId.addTextChangedListener(watcher)
        binding.etPw.addTextChangedListener(watcher)
        binding.etPwCheck.addTextChangedListener(watcher)
    }

    private fun checkEmailExists(email: String) {
        binding.btnCheckId.isEnabled = false
        
        lifecycleScope.launch {
            val result = AppContainer.authRepository.checkEmailExists(email)
            
            binding.btnCheckId.isEnabled = true
            
            result.onSuccess { exists ->
                if (exists) {
                    binding.etId.error = "이미 사용 중인 이메일입니다"
                    Toast.makeText(this@SignUpActivity, "이미 사용 중인 이메일입니다", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@SignUpActivity, "사용 가능한 이메일입니다", Toast.LENGTH_SHORT).show()
                }
            }.onFailure { error ->
                com.example.plant.util.ErrorHandler.handleApiError(
                    this@SignUpActivity,
                    error,
                    "SignUpActivity"
                )
            }
        }
    }

    private fun updateButtonStates() {
        val idText = binding.etId.text.toString().trim()
        val nicknameText = binding.etNickname.text.toString().trim()
        val pwText = binding.etPw.text.toString().trim()
        val pwCheckText = binding.etPwCheck.text.toString().trim()

        // 중복 확인 버튼
        val isIdNotEmpty = idText.isNotEmpty()
        with(binding.btnCheckId) {
            isEnabled = isIdNotEmpty
            backgroundTintList = ColorStateList.valueOf(
                if (isIdNotEmpty) ContextCompat.getColor(context, R.color.button)
                else Color.parseColor("#D9D9D9")
            )
        }

        // 가입하기 버튼
        val isAllFilled = isIdNotEmpty && nicknameText.isNotEmpty() &&
                pwText.isNotEmpty() && pwCheckText.isNotEmpty()

        with(binding.btnSignUp) {
            isEnabled = isAllFilled
            backgroundTintList = ColorStateList.valueOf(
                if (isAllFilled) ContextCompat.getColor(context, R.color.button)
                else Color.parseColor("#D9D9D9")
            )
        }
    }
}
