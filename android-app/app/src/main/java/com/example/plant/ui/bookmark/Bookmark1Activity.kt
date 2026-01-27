package com.example.plant.ui.bookmark

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.plant.databinding.ActivityBookmarkBinding
import com.example.plant.di.AppContainer
import com.example.plant.ui.auth.LoginActivity
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

        if (!AppContainer.firebaseAuthManager.isLoggedIn()) {
            navigateToLogin()
            return
        }

        setupNavigation()
        setupCategoryClickListeners()
        loadSummaryData()
    }

    private fun setupCategoryClickListeners() {
        binding.cvLanguage.setOnClickListener { navigateToResult("꽃말") }
        binding.cvScent.setOnClickListener { navigateToResult("향기") }
        binding.cvSeason.setOnClickListener { navigateToResult("개화시기") }
        binding.cvColor.setOnClickListener { navigateToResult("색상") }

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
                binding.tvTotalCount.text = "총 식물 갯수: ${plants.size}개"
                if (plants.isNotEmpty()) {
                    binding.tvRecommendedSeasonPlant.text = "추천 계절 식물: ${plants[0].name}"
                }
            }.onFailure { error ->
                ErrorHandler.handleAuthRequiredError(this@Bookmark1Activity, error, "Bookmark1Activity")
            }
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

    private fun navigateToLogin() {
        val intent = Intent(this, LoginActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }
}
