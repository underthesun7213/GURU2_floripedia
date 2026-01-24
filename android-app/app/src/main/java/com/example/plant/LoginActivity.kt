package com.example.plant

import android.content.Intent
import android.graphics.Paint
import android.os.Bundle
import android.widget.EditText
import android.widget.ImageView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.AppCompatButton

class LoginActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val tvSignUp = findViewById<TextView>(R.id.tvSignUp)
        val btnLogin = findViewById<AppCompatButton>(R.id.btnLogin)

// 1. 회원가입 글자에 밑줄 긋기
        tvSignUp.paintFlags = tvSignUp.paintFlags or Paint.UNDERLINE_TEXT_FLAG

// 2. 클릭 시 회원가입 화면으로 이동
        tvSignUp.setOnClickListener {
            val intent = Intent(this, SignUpActivity::class.java)
            startActivity(intent)
        }

        btnLogin.setOnClickListener{
            val intent = Intent(this, MainActivity::class.java)
        }

        setContentView(R.layout.activity_login) // XML 화면을 불러옴

        // 1. 사용할 뷰들을 ID로 찾아옵니다.
        val etPassword = findViewById<EditText>(R.id.etPassword)
        val ivPasswordToggle = findViewById<ImageView>(R.id.ivPasswordToggle)

        var isPasswordVisible = false // 상태를 기억할 변수

        // 2. 눈 모양 이미지뷰에 클릭 리스너를 답니다.
        ivPasswordToggle.setOnClickListener {
            isPasswordVisible = !isPasswordVisible

            if (isPasswordVisible) {
                // 비밀번호 보이기: TransformationMethod를 제거함
                etPassword.transformationMethod = null
                ivPasswordToggle.alpha = 1.0f // 밝게 표시
            } else {
                // 비밀번호 숨기기: PasswordTransformationMethod 적용
                etPassword.transformationMethod = android.text.method.PasswordTransformationMethod.getInstance()
                ivPasswordToggle.alpha = 0.5f // 흐리게 표시
            }

            // 중요: 글자 맨 마지막으로 커서를 옮겨줍니다.
            etPassword.setSelection(etPassword.text.length)
        }
    }
}