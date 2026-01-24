package com.example.plant

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.example.plant.databinding.ActivityBookmarkFlowerlanguageBinding

class FlowerLanguageActivity : AppCompatActivity(){
    private lateinit var binding: ActivityBookmarkFlowerlanguageBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        binding = ActivityBookmarkFlowerlanguageBinding.inflate(layoutInflater)
        setContentView(binding.root)

        //뒤로가기 < 버튼을 누르면 꽃갈피 화면으로 돌아감
        binding.btnBack.setOnClickListener {
            val intent = Intent(this, Bookmark1Activity::class.java)
            startActivity(intent)
        }
    }
}