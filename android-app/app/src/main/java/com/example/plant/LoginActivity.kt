package com.example.plant

import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.text.Spannable
import android.text.SpannableString
import android.text.style.ForegroundColorSpan
import android.text.style.StyleSpan
import android.text.style.UnderlineSpan
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class LoginActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // 1. 화면에 XML 레이아웃을 설정합니다.
        setContentView(R.layout.activity_login)

        // 2. XML의 TextView를 ID로 찾습니다.
        val tvSignUpGuide = findViewById<TextView>(R.id.tvSignUpGuide)

        // 3. 스타일을 적용할 전체 문구 설정
        val fullText = "아직 회원이 아니신가요? 회원가입"
        val spannableString = SpannableString(fullText)

        // 4. "회원가입" 글자의 시작과 끝 위치 계산
        val start = fullText.indexOf("회원가입")
        val end = start + "회원가입".length

        // 5. 스타일 적용: 색상을 더 어둡게
        spannableString.setSpan(
            ForegroundColorSpan(Color.parseColor("@color/text1")),
            start, end, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE
        )

        // 6. 스타일 적용: 밑줄 긋기
        spannableString.setSpan(
            UnderlineSpan(),
            start, end, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE
        )

        // 7. 스타일 적용: 굵게(Bold) 만들기
        spannableString.setSpan(
            StyleSpan(Typeface.BOLD),
            start, end, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE
        )

        // 8. 최종 결과물을 TextView에 반영합니다.
        tvSignUpGuide.text = spannableString
    }
}