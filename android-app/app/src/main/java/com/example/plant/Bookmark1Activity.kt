package com.example.plant

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.example.plant.databinding.ActivityBookmarkBinding // 바인딩 클래스명 확인!

class Bookmark1Activity : AppCompatActivity() {

    // 1. binding 변수는 클래스 바로 아래(멤버 변수)에 선언해야 합니다.
    private lateinit var binding: ActivityBookmarkBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 2. 바인딩 초기화 및 레이아웃 설정
        binding = ActivityBookmarkBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // 3. 로고 클릭 리스너
        binding.fixedHeader.imgLogo.setOnClickListener {
            val intent = Intent(this, MainActivity::class.java)
            // 홈으로 갈 때 위에 쌓인 화면들을 제거함
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            startActivity(intent)
        }

        //'꽃말' 카드 클릭 시 상세 화면으로 이동
        binding.cardFlowerLanguage.setOnClickListener {
            // 실제 이동할 액티비티 클래스 이름(예: FlowerLanguageActivity)을 넣어주세요.
            val intent = Intent(this, FlowerLanguageActivity::class.java)
            startActivity(intent)
        }
    }
}