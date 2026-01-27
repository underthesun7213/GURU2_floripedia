package com.example.plant.ui.camera

import android.Manifest
import android.content.ContentValues
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
import com.example.plant.R
import com.example.plant.databinding.ActivityCameraBinding
import com.example.plant.di.AppContainer
import com.example.plant.ui.detail.Detail1Activity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.text.SimpleDateFormat
import java.util.*

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
            capturedImageData?.let { imageData ->
                if (!com.example.plant.util.InputValidator.isValidImageSize(imageData)) {
                    Toast.makeText(this, "이미지 크기는 10MB 이하여야 합니다", Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }
                searchPlantByImage(imageData)
            }
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
        imageCapture.takePicture(
            ContextCompat.getMainExecutor(this),
            object : ImageCapture.OnImageCapturedCallback() {
                override fun onCaptureSuccess(image: ImageProxy) {
                    lifecycleScope.launch { processImage(image) }
                }
                override fun onError(exception: ImageCaptureException) {
                    Toast.makeText(baseContext, "사진 촬영 실패", Toast.LENGTH_SHORT).show()
                }
            }
        )
    }

    private suspend fun processImage(image: ImageProxy) {
        withContext(Dispatchers.IO) {
            try {
                // ImageProxy를 Bitmap으로 변환 (YUV → RGB)
                val bitmap = imageProxyToBitmap(image)
                if (bitmap != null) {
                    val outputStream = ByteArrayOutputStream()
                    bitmap.compress(Bitmap.CompressFormat.JPEG, 85, outputStream)
                    capturedImageData = outputStream.toByteArray()

                    withContext(Dispatchers.Main) { showPreviewMode(bitmap) }
                } else {
                    withContext(Dispatchers.Main) {
                        Toast.makeText(this@CameraActivity, "이미지 처리 실패", Toast.LENGTH_SHORT).show()
                    }
                }
            } finally {
                image.close()
            }
        }
    }

    /**
     * ImageProxy (YUV_420_888)를 Bitmap으로 변환
     */
    private fun imageProxyToBitmap(image: ImageProxy): Bitmap? {
        return try {
            val yBuffer = image.planes[0].buffer
            val uBuffer = image.planes[1].buffer
            val vBuffer = image.planes[2].buffer

            val ySize = yBuffer.remaining()
            val uSize = uBuffer.remaining()
            val vSize = vBuffer.remaining()

            val nv21 = ByteArray(ySize + uSize + vSize)

            // Y, V, U 순서로 복사 (NV21 포맷)
            yBuffer.get(nv21, 0, ySize)
            vBuffer.get(nv21, ySize, vSize)
            uBuffer.get(nv21, ySize + vSize, uSize)

            val yuvImage = android.graphics.YuvImage(
                nv21,
                android.graphics.ImageFormat.NV21,
                image.width,
                image.height,
                null
            )

            val out = ByteArrayOutputStream()
            yuvImage.compressToJpeg(
                android.graphics.Rect(0, 0, image.width, image.height),
                90,
                out
            )

            val jpegBytes = out.toByteArray()
            BitmapFactory.decodeByteArray(jpegBytes, 0, jpegBytes.size)
        } catch (e: Exception) {
            Log.e("CameraActivity", "이미지 변환 실패", e)
            null
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
                com.example.plant.util.ErrorHandler.handleApiError(this@CameraActivity, error, "CameraActivity")
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
