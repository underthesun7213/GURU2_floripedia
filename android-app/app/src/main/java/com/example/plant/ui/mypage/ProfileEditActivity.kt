package com.example.plant.ui.mypage

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.plant.data.remote.TokenManager
import com.example.plant.databinding.ActivityProfileEditBinding
import com.example.plant.di.AppContainer
import com.example.plant.util.LevelAvatar
import kotlinx.coroutines.launch

/**
 * 프로필 편집 화면
 * 프로필 이미지는 레벨 칭호 연동 성장형 아바타로 자동 표시된다 (업로드 없음).
 */
class ProfileEditActivity : AppCompatActivity() {

    private lateinit var binding: ActivityProfileEditBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityProfileEditBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupUI()
        loadUserProfile()
    }

    private fun setupUI() {
        // 닫기 버튼
        binding.btnClose.setOnClickListener {
            finish()
        }

        // 저장 버튼
        binding.btnSave.setOnClickListener {
            saveProfile()
        }

        // 데이터(기록) 삭제 버튼
        binding.tvDeleteAccount.setOnClickListener {
            showDeleteAccountDialog()
        }
    }

    private fun showDeleteAccountDialog() {
        AlertDialog.Builder(this)
            .setTitle("데이터 삭제")
            .setMessage("이 기기의 찜·레벨 기록이 모두 삭제됩니다.\n삭제 후에는 복구할 수 없습니다.")
            .setPositiveButton("삭제") { _, _ ->
                performDeleteAccount()
            }
            .setNegativeButton("취소", null)
            .show()
    }

    private fun performDeleteAccount() {
        binding.progressBar.visibility = View.VISIBLE

        lifecycleScope.launch {
            val result = AppContainer.userRepository.deleteAccount()

            binding.progressBar.visibility = View.GONE

            result.onSuccess { message ->
                // 로컬 로그아웃 처리
                AppContainer.firebaseAuthManager.signOut()
                TokenManager.clearToken(this@ProfileEditActivity)

                Toast.makeText(this@ProfileEditActivity, "데이터가 삭제되었습니다", Toast.LENGTH_SHORT).show()
                navigateToHome()
            }.onFailure { error ->
                com.example.plant.util.ErrorHandler.handleApiError(
                    this@ProfileEditActivity,
                    error,
                    "ProfileEditActivity"
                )
            }
        }
    }

    // 익명 인증 모델: 데이터 삭제 후 로그인 화면이 없으므로 홈으로 이동.
    // 홈(MainActivity)에서 익명 세션이 새로 확보된다.
    private fun navigateToHome() {
        val intent = Intent(this, com.example.plant.ui.home.MainActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }

    private fun loadUserProfile() {
        binding.progressBar.visibility = View.VISIBLE

        lifecycleScope.launch {
            val result = AppContainer.userRepository.getMyProfile()

            binding.progressBar.visibility = View.GONE

            result.onSuccess { user ->
                binding.etNickname.setText(user.nickname)
                LevelAvatar.apply(binding.ivProfile, user.levelInfo?.level ?: 1)
            }.onFailure { error ->
                com.example.plant.util.ErrorHandler.handleApiError(
                    this@ProfileEditActivity,
                    error,
                    "ProfileEditActivity"
                )
            }
        }
    }

    private fun saveProfile() {
        val newNickname = binding.etNickname.text.toString().trim()

        if (newNickname.isEmpty()) {
            Toast.makeText(this, "닉네임을 입력해주세요", Toast.LENGTH_SHORT).show()
            return
        }

        if (newNickname.length < 2 || newNickname.length > 20) {
            Toast.makeText(this, "닉네임은 2자 이상 20자 이하로 입력해주세요", Toast.LENGTH_SHORT).show()
            return
        }

        binding.progressBar.visibility = View.VISIBLE
        binding.btnSave.isEnabled = false

        lifecycleScope.launch {
            // 닉네임 업데이트
            val result = AppContainer.userRepository.updateProfile(
                nickname = newNickname,
                profileImageUrl = null
            )

            binding.progressBar.visibility = View.GONE
            binding.btnSave.isEnabled = true

            result.onSuccess { user ->
                Toast.makeText(this@ProfileEditActivity, "프로필이 수정되었습니다", Toast.LENGTH_SHORT).show()
                finish()
            }.onFailure { error ->
                com.example.plant.util.ErrorHandler.handleApiError(
                    this@ProfileEditActivity,
                    error,
                    "ProfileEditActivity"
                )
            }
        }
    }
}
