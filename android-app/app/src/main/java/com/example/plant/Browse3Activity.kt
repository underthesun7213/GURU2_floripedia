package com.example.plant

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.plant.databinding.ActivityBrowse3Binding // XML 이름에 맞는 바인딩 클래스

class Browse3Activity : AppCompatActivity() {

    // View Binding 객체 선언
    private lateinit var binding: ActivityBrowse3Binding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 1. 바인딩 초기화
        binding = ActivityBrowse3Binding.inflate(layoutInflater)
        setContentView(binding.root)

        // 2. '뒤로가기' 버튼 클릭 시 (상단 이미지 버튼)
        binding.btnBack.setOnClickListener {
            finish() // 현재 액티비티 종료하고 이전 화면으로 이동
        }

        // 3. '꽃갈피에 저장' 버튼 클릭 시
        binding.btnSave.setOnClickListener {
            // 토스트 메시지 출력
            Toast.makeText(this, "꽃갈피에 저장되었습니다", Toast.LENGTH_SHORT).show()
        }

        // 4. '재탐색' 버튼 클릭 시 Browse1Activity로 이동
        binding.btnRetry.setOnClickListener {
            // Browse1Activity가 있다고 가정합니다. (클래스명이 다르면 수정해주세요!)
            val intent = Intent(this, Browse1Activity::class.java)

            // 새로운 탐색을 시작하는 것이므로, 이전의 탐색 기록(Browse2, 3)을 스택에서 제거하고 싶을 때 사용
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            startActivity(intent)
            finish() // 현재 화면은 닫아줌
        }
    }
}