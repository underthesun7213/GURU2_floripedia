package com.example.plant.ui.browse

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.GridLayoutManager
import com.example.plant.databinding.ActivityBrowse2Binding
import com.example.plant.di.AppContainer
import com.example.plant.ui.home.MainActivity
import com.example.plant.ui.detail.Detail1Activity
import com.example.plant.ui.camera.CameraActivity
import com.example.plant.ui.bookmark.Bookmark1Activity
import com.example.plant.ui.components.FloripediaBottomBar
import com.example.plant.ui.mypage.MyPageActivity
import kotlinx.coroutines.launch

class Browse2Activity : AppCompatActivity() {

    private lateinit var binding: ActivityBrowse2Binding
    private lateinit var plantAdapter: PlantCardAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        binding = ActivityBrowse2Binding.inflate(layoutInflater)
        setContentView(binding.root)

        // Intent에서 검색어 받기
        val searchQuery = intent.getStringExtra("search_query")

        binding.fixedHeader.imgLogo.setOnClickListener {
            val intent = Intent(this, MainActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            startActivity(intent)
        }

        // 사용자 아이콘 클릭 → 마이페이지
        binding.fixedHeader.imgUser.setOnClickListener {
            val intent = Intent(this, MyPageActivity::class.java)
            startActivity(intent)
        }

        // 검색 버튼 → 탐색 화면으로 이동
        binding.btnSearch.setOnClickListener {
            val situation = binding.etUserStoryResult.text.toString().trim()
            if (!com.example.plant.util.InputValidator.isNotEmpty(situation)) {
                Toast.makeText(this, "상황을 입력해주세요", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            if (!com.example.plant.util.InputValidator.isValidSituation(situation)) {
                Toast.makeText(this, "상황은 10자 이상 500자 이하로 입력해주세요", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            // Browse3Activity로 이동하면서 상황 전달
            val intent = Intent(this, Browse3Activity::class.java).apply {
                putExtra("situation", situation)
            }
            startActivity(intent)
        }

        setupNavigation()
        setupSearchResults()

        // 검색어가 있으면 검색 결과 표시, 없으면 탐색 화면 유지
        if (!searchQuery.isNullOrEmpty()) {
            searchPlants(searchQuery)
        }
    }

    private fun setupNavigation() {
        binding.bottomNav.composeViewBottomNav.setContent {
            FloripediaBottomBar(
                selectedMenu = "search",
                onNavigate = { menu ->
                    when (menu) {
                        "home" -> {
                            val intent = Intent(this, MainActivity::class.java)
                            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
                            startActivity(intent)
                        }
                        "bookmark" -> {
                            startActivity(Intent(this, Bookmark1Activity::class.java))
                        }
                        "my" -> {
                            startActivity(Intent(this, MyPageActivity::class.java))
                        }
                    }
                },
                onCameraClick = {
                    startActivity(Intent(this, CameraActivity::class.java))
                }
            )
        }
    }

    private fun setupSearchResults() {
        // 검색 결과 리스트의 식물 카드 클릭 → Detail1Activity
        plantAdapter = PlantCardAdapter { plant ->
            val intent = Intent(this, Detail1Activity::class.java).apply {
                putExtra("plant_id", plant.id)
                putExtra("plant_name", plant.name)
            }
            startActivity(intent)
        }
        
        binding.rvSearchResults.adapter = plantAdapter
        binding.rvSearchResults.layoutManager = GridLayoutManager(this, 2)
    }

    private fun searchPlants(keyword: String) {
        // Validation: 검색어 검증
        if (!com.example.plant.util.InputValidator.isValidSearchKeyword(keyword)) {
            Toast.makeText(this, "검색어는 1자 이상 100자 이하로 입력해주세요", Toast.LENGTH_SHORT).show()
            return
        }

        // 검색 결과 영역 표시
        binding.centerContent.visibility = View.GONE
        binding.inputCard.visibility = View.GONE
        binding.btnSearch.visibility = View.GONE
        binding.rvSearchResults.visibility = View.VISIBLE

        lifecycleScope.launch {
            val result = AppContainer.plantRepository.getPlants(keyword = keyword)
            
            result.onSuccess { plants ->
                plantAdapter.submitList(plants)
                if (plants.isEmpty()) {
                    Toast.makeText(this@Browse2Activity, "검색 결과가 없습니다", Toast.LENGTH_SHORT).show()
                }
            }.onFailure { error ->
                com.example.plant.util.ErrorHandler.handleApiError(
                    this@Browse2Activity,
                    error,
                    "Browse2Activity"
                )
            }
        }
    }
}
