package com.example.plant

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.res.ResourcesCompat
import com.example.plant.databinding.ActivityDetail1Binding

class Detail1Activity : AppCompatActivity() {

    // 뷰 바인딩 객체 선언
    private lateinit var binding: ActivityDetail1Binding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 바인딩 초기화 및 레이아웃 설정
        binding = ActivityDetail1Binding.inflate(layoutInflater)
        setContentView(binding.root)

        // 꽃갈피 버튼 클릭 이벤트
        binding.btnBookmark.setOnClickListener {
            Toast.makeText(this, "꽃갈피에 저장되었습니다", Toast.LENGTH_SHORT).show()

            with(binding.btnBookmark) {
                setBackgroundResource(R.drawable.bg_tag_gray)
                text = "이미 꽃갈피에 있어요"
                typeface = ResourcesCompat.getFont(context, R.font.pretendardsemibold)

                // 버튼 비활성화 (더 이상 클릭되지 않게 함)
                isEnabled = false
            }
        }

        // 1. fixedHeader 내부에 있는 imgLogo를 찾아 클릭 리스너 연결
        binding.fixedHeader.imgLogo.setOnClickListener {
            // 2. 하단바의 selectedItemId를 홈 메뉴 ID로 변경
            // 이렇게 하면 이전에 설정한 setOnItemSelectedListener가 자동으로 실행되어 홈 화면으로 바뀝니다.
            binding.bottomNav.selectedItemId = R.id.menu_home

            // (선택 사항) 만약 화면이 스크롤 된 상태라면 맨 위로 올려주는 효과를 줄 수도 있어요.
            binding.scrollView.smoothScrollTo(0, 0)
        }
    }
}