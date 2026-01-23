package com.example.plant

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity // 1. 상속을 위해 필요
import com.example.plant.databinding.ActivityBrowse2Binding // 2. 본인의 레이아웃 바인딩 클래스

class Browse2Activity : AppCompatActivity() {

    // 멤버 변수로 선언 (onCreate 밖)
    private lateinit var binding: ActivityBrowse2Binding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 바인딩 초기화 및 레이아웃 설정
        binding = ActivityBrowse2Binding.inflate(layoutInflater)
        setContentView(binding.root)

        // 1. 헤더 로고 클릭 시 홈 화면(MainActivity)으로 이동
        binding.fixedHeader.imgLogo.setOnClickListener {
            val intent = Intent(this, MainActivity::class.java)
            // 홈으로 갈 때 위에 쌓인 화면들을 제거함
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            startActivity(intent)
        }

        // 2. '탐색하기' 버튼 클릭 시 Browse3Activity로 이동
        binding.btnSearch.setOnClickListener {
            val intent = Intent(this, Browse3Activity::class.java)
            startActivity(intent) // 3. 이 명령어가 있어야 실제로 화면이 넘어갑니다!
        }
    }
}