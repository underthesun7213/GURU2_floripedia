package com.example.plant.ui.mypage

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import coil.load
import com.example.plant.R
import com.example.plant.databinding.ActivityProfileEditBinding
import com.example.plant.di.AppContainer
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream

/**
 * 프로필 편집 화면
 */
class ProfileEditActivity : AppCompatActivity() {

    private lateinit var binding: ActivityProfileEditBinding
    private var selectedImageUri: Uri? = null
    private var pendingImageData: ByteArray? = null

    // 이미지 선택 런처
    private val imagePickerLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let { handleSelectedImage(it) }
    }

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

        // 프로필 사진 변경 버튼
        binding.btnChangePhoto.setOnClickListener {
            openImagePicker()
        }

        // 저장 버튼
        binding.btnSave.setOnClickListener {
            saveProfile()
        }
    }

    private fun openImagePicker() {
        imagePickerLauncher.launch("image/*")
    }

    private fun handleSelectedImage(uri: Uri) {
        selectedImageUri = uri

        // 미리보기 표시
        binding.ivProfile.load(uri) {
            crossfade(true)
            placeholder(R.drawable.ic_profile_placeholder)
            error(R.drawable.ic_profile_placeholder)
        }

        // 이미지 압축 및 바이트 변환 (백그라운드)
        lifecycleScope.launch {
            pendingImageData = compressImage(uri)
        }
    }

    /**
     * 이미지 압축 (최대 500KB, 800x800)
     */
    private suspend fun compressImage(uri: Uri): ByteArray? = withContext(Dispatchers.IO) {
        try {
            val inputStream = contentResolver.openInputStream(uri) ?: return@withContext null
            val originalBitmap = BitmapFactory.decodeStream(inputStream)
            inputStream.close()

            // 리사이즈 (최대 800x800)
            val maxSize = 800
            val ratio = minOf(
                maxSize.toFloat() / originalBitmap.width,
                maxSize.toFloat() / originalBitmap.height,
                1f
            )
            val newWidth = (originalBitmap.width * ratio).toInt()
            val newHeight = (originalBitmap.height * ratio).toInt()
            val resizedBitmap = Bitmap.createScaledBitmap(originalBitmap, newWidth, newHeight, true)

            // 압축 (JPEG, 품질 조정하여 500KB 이하로)
            val outputStream = ByteArrayOutputStream()
            var quality = 90
            do {
                outputStream.reset()
                resizedBitmap.compress(Bitmap.CompressFormat.JPEG, quality, outputStream)
                quality -= 10
            } while (outputStream.size() > 500 * 1024 && quality > 10)

            if (resizedBitmap != originalBitmap) {
                resizedBitmap.recycle()
            }
            originalBitmap.recycle()

            outputStream.toByteArray()
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    private fun loadUserProfile() {
        binding.progressBar.visibility = View.VISIBLE

        lifecycleScope.launch {
            val result = AppContainer.userRepository.getMyProfile()

            binding.progressBar.visibility = View.GONE

            result.onSuccess { user ->
                binding.etNickname.setText(user.nickname)
                binding.etEmail.setText(user.email)

                user.profileImageUrl?.let { url ->
                    binding.ivProfile.load(url) {
                        crossfade(true)
                        placeholder(R.drawable.ic_profile_placeholder)
                        error(R.drawable.ic_profile_placeholder)
                    }
                }
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
            // 이미지가 선택된 경우 먼저 업로드
            if (pendingImageData != null) {
                val imageResult = uploadProfileImage()
                if (imageResult.isFailure) {
                    binding.progressBar.visibility = View.GONE
                    binding.btnSave.isEnabled = true
                    com.example.plant.util.ErrorHandler.handleApiError(
                        this@ProfileEditActivity,
                        imageResult.exceptionOrNull() ?: Exception("이미지 업로드 실패"),
                        "ProfileEditActivity"
                    )
                    return@launch
                }
            }

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

    /**
     * 프로필 이미지 업로드
     */
    private suspend fun uploadProfileImage(): Result<Unit> {
        val imageData = pendingImageData ?: return Result.failure(Exception("이미지 데이터가 없습니다"))

        val fileName = "profile_${System.currentTimeMillis()}.jpg"
        val contentType = "image/jpeg"

        val result = AppContainer.userRepository.uploadProfileImage(
            imageData = imageData,
            fileName = fileName,
            contentType = contentType
        )

        return result.map { Unit }
    }
}
