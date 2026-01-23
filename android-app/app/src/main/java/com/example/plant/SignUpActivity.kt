package com.example.plant

import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.example.plant.R // R 클래스 임포트
import com.example.plant.databinding.ActivitySignupBinding
import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.result.contract.ActivityResultContracts
import android.net.Uri

class SignUpActivity : AppCompatActivity() {
    private lateinit var binding: ActivitySignupBinding // 바인딩 클래스명 확인 필요

    // 1. 갤러리에서 사진을 가져온 후 실행될 동작 정의
    private val pickImageLauncher = registerForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        uri?.let {
            // 선택한 이미지를 프로필 이미지 뷰에 설정
            binding.ivProfileSelect.setImageURI(it)
        }
    }

    // 2. 권한 요청을 위한 런처
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

        // 프로필 추가 버튼(+) 클릭 시
        binding.btnProfileAdd.setOnClickListener {
            checkPermissionAndOpenGallery()
        }


        // 1. 실시간 입력 감시 설정
        setupTextWatchers()

        // 2. 중복 확인 버튼 클릭
        binding.btnCheckId.setOnClickListener { // XML에서 중복확인 버튼 ID를 btnCheckId로 추가하세요
            Toast.makeText(this, "사용 가능한 아이디 입니다", Toast.LENGTH_SHORT).show()
        }

        // 3. 가입하기 버튼 클릭
        binding.btnSignUp.setOnClickListener {
            val intent = Intent(this, MainActivity::class.java)
            // 가입 후 백버튼을 눌렀을 때 다시 회원가입 화면으로 오지 않도록 설정
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(intent)
        }

        // 4. 뒤로가기(X) 버튼
        binding.btnBack.setOnClickListener { finish() }


    }

    private fun checkPermissionAndOpenGallery() {
        val permission = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            Manifest.permission.READ_MEDIA_IMAGES
        } else {
            Manifest.permission.READ_EXTERNAL_STORAGE
        }

        when {
            ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED -> {
                // 권한이 이미 있는 경우
                openGallery()
            }
            else -> {
                // 권한 요청
                requestPermissionLauncher.launch(permission)
            }
        }
    }

    private fun openGallery() {
        // 갤러리 앱 열기 (이미지 타입만 필터링)
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

        // 모든 EditText에 리스너 등록
        binding.etNickname.addTextChangedListener(watcher)
        binding.etId.addTextChangedListener(watcher)
        binding.etPw.addTextChangedListener(watcher)
        binding.etPwCheck.addTextChangedListener(watcher)
    }

    private fun updateButtonStates() {
        val idText = binding.etId.text.toString().trim()
        val nicknameText = binding.etNickname.text.toString().trim()
        val pwText = binding.etPw.text.toString().trim()
        val pwCheckText = binding.etPwCheck.text.toString().trim()

        // 중복 확인 버튼 활성화 조건 (아이디 입력 시)
        val isIdNotEmpty = idText.isNotEmpty()
        with(binding.btnCheckId) { // XML에서 중복확인 버튼에 ID를 지정해야 함
            isEnabled = isIdNotEmpty
            backgroundTintList = ColorStateList.valueOf(
                if (isIdNotEmpty) ContextCompat.getColor(context, R.color.button)
                else Color.parseColor("#D9D9D9")
            )
        }

        // 가입하기 버튼 활성화 조건 (모든 칸이 비어있지 않을 때)
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