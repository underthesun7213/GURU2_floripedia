package com.example.plant

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.plant.databinding.ActivityBrowse1Binding

class Browse1Activity : AppCompatActivity() {
    private lateinit var binding: ActivityBrowse1Binding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBrowse1Binding.inflate(layoutInflater)
        setContentView(binding.root)

        // EditText에서 키보드 엔터(완료) 버튼을 눌렀을 때 처리
        binding.etUserStory.setOnEditorActionListener { v, actionId, event ->
            // 키보드의 '완료' 버튼 혹은 엔터 키가 눌렸을 때
            if (actionId == android.view.inputmethod.EditorInfo.IME_ACTION_DONE ||
                actionId == android.view.inputmethod.EditorInfo.IME_ACTION_NEXT) {

                val userStory = binding.etUserStory.text.toString()

                if (userStory.isNotEmpty()) {
                    val intent = Intent(this, Browse2Activity::class.java)
                    intent.putExtra("story", userStory) // 데이터 전달
                    startActivity(intent)
                    true // 이벤트 처리 완료
                } else {
                    Toast.makeText(this, "이야기를 입력해주세요!", Toast.LENGTH_SHORT).show()
                    false
                }
            } else {
                false
            }
        }
    }
}