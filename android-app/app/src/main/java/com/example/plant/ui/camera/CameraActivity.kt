package com.example.plant.ui.camera

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.example.plant.databinding.ActivityCameraBinding
import com.example.plant.data.repository.PartialPlantException
import com.example.plant.di.AppContainer
import com.example.plant.ui.detail.Detail1Activity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream

class CameraActivity : AppCompatActivity() {
    private lateinit var binding: ActivityCameraBinding
    private var imageCapture: ImageCapture? = null
    private var capturedImageData: ByteArray? = null
    private var isFrontCamera = false

    // 최신 Activity Result API용 런처 등록
    private lateinit var galleryLauncher: ActivityResultLauncher<Intent>

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCameraBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // 갤러리 런처 초기화
        galleryLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == RESULT_OK && result.data != null) {
                handleGalleryResult(result.data?.data)
            }
        }

        if (allPermissionsGranted()) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(this, REQUIRED_PERMISSIONS, REQUEST_CODE_PERMISSIONS)
        }

        setupUI()
    }

    private fun setupUI() {
        binding.btnCapture.setOnClickListener { takePhoto() }

        binding.btnSearch.setOnClickListener {
            val imageData = capturedImageData
            if (imageData == null) {
                Toast.makeText(this, "먼저 사진을 촬영하거나 선택해주세요", Toast.LENGTH_SHORT).show()
                Log.e("CameraActivity", "capturedImageData is null")
                return@setOnClickListener
            }
            if (!com.example.plant.util.InputValidator.isValidImageSize(imageData)) {
                Toast.makeText(this, "이미지 크기는 10MB 이하여야 합니다", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            Log.d("CameraActivity", "이미지 검색 시작, size=${imageData.size}")
            searchPlantByImage(imageData)
        }

        binding.btnRetake.setOnClickListener { showCameraMode() }

        binding.btnGallery.setOnClickListener { openGallery() }

        binding.btnSwitch.setOnClickListener { switchCamera() }

        binding.btnBack.setOnClickListener { finish() }

        showCameraMode()
    }

    private fun openGallery() {
        val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
            type = "image/*"
            addCategory(Intent.CATEGORY_OPENABLE)
        }
        val pickIntent = Intent(Intent.ACTION_PICK, MediaStore.Images.Media.EXTERNAL_CONTENT_URI)
        val chooserIntent = Intent.createChooser(intent, "이미지 선택").apply {
            putExtra(Intent.EXTRA_INITIAL_INTENTS, arrayOf(pickIntent))
        }

        // startActivityForResult 대신 런처 사용
        galleryLauncher.launch(chooserIntent)
    }

    private fun handleGalleryResult(uri: Uri?) {
        uri?.let {
            lifecycleScope.launch {
                try {
                    val inputStream = contentResolver.openInputStream(it)
                    val imageData = inputStream?.readBytes()
                    inputStream?.close()

                    imageData?.let { data ->
                        capturedImageData = data
                        val bitmap = BitmapFactory.decodeByteArray(data, 0, data.size)
                        showPreviewMode(bitmap)
                        Toast.makeText(this@CameraActivity, "이미지 선택 완료! 검색 버튼을 눌러주세요.", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    Log.e("CameraActivity", "이미지 로드 실패", e)
                }
            }
        }
    }

    private fun showCameraMode() {
        binding.viewFinder.visibility = View.VISIBLE
        binding.ivCapturedImage.visibility = View.GONE
        binding.layoutBeforeCapture.visibility = View.VISIBLE
        binding.layoutAfterCapture.visibility = View.GONE
        capturedImageData = null
    }

    private fun showPreviewMode(bitmap: Bitmap) {
        binding.viewFinder.visibility = View.GONE
        binding.ivCapturedImage.visibility = View.VISIBLE
        binding.ivCapturedImage.setImageBitmap(bitmap)
        binding.layoutBeforeCapture.visibility = View.GONE
        binding.layoutAfterCapture.visibility = View.VISIBLE
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider: ProcessCameraProvider = cameraProviderFuture.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.viewFinder.surfaceProvider)
            }
            imageCapture = ImageCapture.Builder().build()
            val cameraSelector = if (isFrontCamera) CameraSelector.DEFAULT_FRONT_CAMERA else CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageCapture)
            } catch (exc: Exception) {
                Log.e("CameraX", "카메라 실행 실패", exc)
            }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun switchCamera() {
        isFrontCamera = !isFrontCamera
        startCamera()
    }

    private fun takePhoto() {
        val imageCapture = imageCapture ?: return

        // 임시 파일로 저장 (YUV 변환 문제 회피)
        val photoFile = java.io.File(
            cacheDir,
            "capture_${System.currentTimeMillis()}.jpg"
        )
        val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()

        imageCapture.takePicture(
            outputOptions,
            ContextCompat.getMainExecutor(this),
            object : ImageCapture.OnImageSavedCallback {
                override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                    lifecycleScope.launch { processImageFile(photoFile) }
                }
                override fun onError(exception: ImageCaptureException) {
                    Log.e("CameraActivity", "사진 촬영 실패", exception)
                    Toast.makeText(baseContext, "사진 촬영 실패", Toast.LENGTH_SHORT).show()
                }
            }
        )
    }

    private suspend fun processImageFile(photoFile: java.io.File) {
        withContext(Dispatchers.IO) {
            try {
                Log.d("CameraActivity", "processImageFile: ${photoFile.absolutePath}, exists=${photoFile.exists()}, size=${photoFile.length()}")

                val bitmap = BitmapFactory.decodeFile(photoFile.absolutePath)
                if (bitmap != null) {
                    Log.d("CameraActivity", "Bitmap 생성 성공: ${bitmap.width}x${bitmap.height}")
                    val outputStream = ByteArrayOutputStream()
                    bitmap.compress(Bitmap.CompressFormat.JPEG, 85, outputStream)
                    capturedImageData = outputStream.toByteArray()
                    Log.d("CameraActivity", "capturedImageData 설정 완료: ${capturedImageData?.size} bytes")

                    withContext(Dispatchers.Main) { showPreviewMode(bitmap) }
                } else {
                    Log.e("CameraActivity", "BitmapFactory.decodeFile 반환값 null")
                    withContext(Dispatchers.Main) {
                        Toast.makeText(this@CameraActivity, "이미지 처리 실패", Toast.LENGTH_SHORT).show()
                    }
                }
                // 임시 파일 삭제
                photoFile.delete()
            } catch (e: Exception) {
                Log.e("CameraActivity", "이미지 처리 실패", e)
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@CameraActivity, "이미지 처리 실패: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun searchPlantByImage(imageData: ByteArray) {
        binding.progressBar.visibility = View.VISIBLE
        binding.btnSearch.isEnabled = false

        lifecycleScope.launch {
            val result = AppContainer.plantRepository.searchByImage(
                imageData = imageData,
                fileName = "search_${System.currentTimeMillis()}.jpg"
            )
            binding.progressBar.visibility = View.GONE
            binding.btnSearch.isEnabled = true

            result.onSuccess { plantResult ->
                val intent = Intent(this@CameraActivity, Detail1Activity::class.java).apply {
                    putExtra("plant_id", plantResult.id)
                    putExtra("plant_name", plantResult.name)
                }
                startActivity(intent)
                finish()
            }.onFailure { error ->
                when (error) {
                    is PartialPlantException -> {
                        // 이름은 찾았지만 상세정보 실패
                        Toast.makeText(
                            this@CameraActivity,
                            "상세정보를 불러오지 못했습니다. 이름은 ${error.plantName}입니다",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                    else -> {
                        // 완전 실패
                        Toast.makeText(
                            this@CameraActivity,
                            "식물을 인식하지 못했습니다",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }
            }
        }
    }

    private fun allPermissionsGranted() = REQUIRED_PERMISSIONS.all {
        ContextCompat.checkSelfPermission(baseContext, it) == PackageManager.PERMISSION_GRANTED
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CODE_PERMISSIONS && allPermissionsGranted()) {
            startCamera()
        }
    }

    companion object {
        private const val REQUEST_CODE_PERMISSIONS = 10
        private val REQUIRED_PERMISSIONS = arrayOf(Manifest.permission.CAMERA)
    }
}