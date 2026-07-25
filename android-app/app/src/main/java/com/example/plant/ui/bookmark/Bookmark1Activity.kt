package com.example.plant.ui.bookmark

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.plant.R
import com.example.plant.databinding.ActivityBookmarkBinding
import com.example.plant.di.AppContainer
import com.example.plant.ui.home.MainActivity
import com.example.plant.ui.camera.CameraActivity
import com.example.plant.ui.components.FloripediaBottomBar
import com.example.plant.ui.mypage.MyPageActivity
import com.example.plant.util.ErrorHandler
import kotlinx.coroutines.launch

class Bookmark1Activity : AppCompatActivity() {

    private lateinit var binding: ActivityBookmarkBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBookmarkBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // 익명 세션은 앱 시작 시 확보됨 → 별도 로그인 게이트 불필요
        setupNavigation()
        setupCategoryClickListeners()
        loadSummaryData()
    }

    private fun setupCategoryClickListeners() {
        binding.cvLanguage.setOnClickListener { navigateToResult(getString(R.string.category_flower_language)) }
        binding.cvScent.setOnClickListener { navigateToResult(getString(R.string.category_scent)) }
        binding.cvSeason.setOnClickListener { navigateToResult(getString(R.string.category_blooming_season)) }
        binding.cvColor.setOnClickListener { navigateToResult(getString(R.string.category_color)) }

        binding.fixedHeader.imgLogo.setOnClickListener {
            val intent = Intent(this, MainActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            startActivity(intent)
        }
        
        binding.fixedHeader.imgUser.setOnClickListener {
            startActivity(Intent(this, MyPageActivity::class.java))
        }
    }

    private fun loadSummaryData() {
        lifecycleScope.launch {
            val result = AppContainer.userRepository.getMyFavorites()
            result.onSuccess { plants ->
                binding.tvTotalCount.text = getString(R.string.bookmark_total_count_format, plants.size)
                // "추천 계절 식물": 현재 계절에 해당하는 찜을 우선 선택 (없으면 첫 찜으로 폴백).
                // 기존엔 계절과 무관하게 plants[0]만 보여줘 라벨과 동작이 불일치했음.
                val season = currentSeason()
                val pick = plants.firstOrNull { it.season == season } ?: plants.firstOrNull()
                if (pick != null) {
                    binding.tvRecommendedSeasonPlant.text = getString(R.string.bookmark_recommended_format, pick.name)
                }
            }.onFailure { error ->
                ErrorHandler.handleAuthRequiredError(this@Bookmark1Activity, error, "Bookmark1Activity")
            }
        }
    }

    /** 기기 날짜 기준 현재 계절 (백엔드 season 코드와 동일 규약) */
    private fun currentSeason(): String {
        val month = java.util.Calendar.getInstance().get(java.util.Calendar.MONTH) + 1
        return when (month) {
            in 3..5 -> "SPRING"
            in 6..8 -> "SUMMER"
            in 9..11 -> "FALL"
            else -> "WINTER"
        }
    }

    private fun navigateToResult(category: String) {
        val intent = Intent(this, BookmarkCategoryActivity::class.java).apply {
            putExtra("category", category)
        }
        startActivity(intent)
    }

    private fun setupNavigation() {
        binding.bottomNav.composeViewBottomNav.setContent {
            FloripediaBottomBar(
                selectedMenu = "bookmark",
                onNavigate = { menu ->
                    when (menu) {
                        "home" -> {
                            val intent = Intent(this, MainActivity::class.java)
                            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
                            startActivity(intent)
                        }
                        "search" -> startActivity(Intent(this, com.example.plant.ui.browse.Browse2Activity::class.java))
                        "my" -> startActivity(Intent(this, MyPageActivity::class.java))
                    }
                },
                onCameraClick = { startActivity(Intent(this, CameraActivity::class.java)) }
            )
        }
    }

}
