package com.example.plant.ui.browse

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import coil.load
import com.example.plant.R
import com.example.plant.data.remote.dto.response.PlantExploreDto
import com.example.plant.databinding.ActivityBrowse3Binding
import com.example.plant.di.AppContainer
import com.example.plant.ui.detail.Detail1Activity
import com.example.plant.ui.camera.CameraActivity
import com.example.plant.ui.home.MainActivity
import com.example.plant.ui.bookmark.Bookmark1Activity
import com.example.plant.ui.components.FloripediaBottomBar
import com.example.plant.ui.mypage.MyPageActivity
import kotlinx.coroutines.launch

/**
 * 탐색 결과 화면
 */
class Browse3Activity : AppCompatActivity() {

    private lateinit var binding: ActivityBrowse3Binding
    private var recommendedPlant: PlantExploreDto? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBrowse3Binding.inflate(layoutInflater)
        setContentView(binding.root)

        val situation = intent.getStringExtra("situation")

        setupNavigation()
        setupUI()

        if (situation != null) {
            showRecommendationResult(situation)
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
                        "bookmark" -> startActivity(Intent(this, Bookmark1Activity::class.java))
                        "my" -> startActivity(Intent(this, MyPageActivity::class.java))
                    }
                },
                onCameraClick = {
                    startActivity(Intent(this, CameraActivity::class.java))
                }
            )
        }
    }

    private fun setupUI() {
        // 뒤로가기
        binding.btnBack.setOnClickListener {
            finish()
        }

        // 재탐색 버튼
        binding.btnRetry.setOnClickListener {
            val intent = Intent(this, Browse2Activity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            startActivity(intent)
        }
    }

    private fun showRecommendationResult(situation: String) {
        binding.loadingOverlay.visibility = View.VISIBLE
        binding.scrollView.visibility = View.GONE

        lifecycleScope.launch {
            val result = AppContainer.plantRepository.recommendPlant(situation)

            binding.loadingOverlay.visibility = View.GONE
            binding.scrollView.visibility = View.VISIBLE

            result.onSuccess { plant ->
                recommendedPlant = plant
                displayPlantInfo(plant)
            }.onFailure { error ->
                com.example.plant.util.ErrorHandler.handleApiError(
                    this@Browse3Activity,
                    error,
                    "Browse3Activity"
                )
            }
        }
    }

    private fun displayPlantInfo(plant: PlantExploreDto) {
        binding.tvPlantName.text = plant.name
        binding.tvInfoHeader.text = "${plant.name}(꽃 이름)"
        binding.tvRecommendationEssay.text = plant.recommendation

        plant.imageUrl.let { url ->
            binding.ivPlantImage.load(url) {
                crossfade(true)
                placeholder(R.drawable.bg_image_placeholder)
                error(R.drawable.bg_image_placeholder)
            }
        }

        // 꽃말 태그 (PlantExploreDto 에는 flowerLanguage 가 없음. recommendation 이나 다른 필드 활용 필요하나 
        // 레이아웃 구조상 숨김 처리 하거나 고정값 처리)
        val tagViews = listOf(binding.tvTag1, binding.tvTag2, binding.tvTag3, binding.tvTag4)
        tagViews.forEach { it.visibility = View.GONE }

        // 정보 카드
        binding.tvCategory.text = plant.category
        
        val seasonKorean = when (plant.season.uppercase()) {
            "SPRING" -> "봄"; "SUMMER" -> "여름"; "FALL" -> "가을"; "WINTER" -> "겨울"; else -> plant.season
        }
        binding.tvSeason.text = seasonKorean
        binding.ivSeason.setImageResource(
            when (plant.season.uppercase()) {
                "SPRING" -> R.drawable.spring
                "SUMMER" -> R.drawable.summer
                "FALL" -> R.drawable.autumn
                "WINTER" -> R.drawable.winter
                else -> R.drawable.spring
            }
        )

        // PlantExploreDto 에는 scent, color 필드가 없고 scentTags, colorLabel 등이 있음
        binding.tvScent.text = plant.scentTags.firstOrNull() ?: "은은한 향"
        binding.tvColor.text = plant.colorLabel
        
        plant.hexCode.let { hex ->
            try {
                binding.viewColor.setBackgroundColor(Color.parseColor(if (hex.startsWith("#")) hex else "#$hex"))
            } catch (e: Exception) {
                binding.viewColor.setBackgroundColor(resources.getColor(R.color.button, null))
            }
        }

        binding.cardPlantImage.setOnClickListener { navigateToDetail(plant) }
        binding.tvMoreInfo.setOnClickListener { navigateToDetail(plant) }
        binding.btnSave.setOnClickListener { saveToFavorites(plant.id) }
    }

    private fun navigateToDetail(plant: PlantExploreDto) {
        val intent = Intent(this, Detail1Activity::class.java).apply {
            putExtra("plant_id", plant.id)
            putExtra("plant_name", plant.name)
        }
        startActivity(intent)
    }

    private fun saveToFavorites(plantId: String) {
        lifecycleScope.launch {
            val result = AppContainer.userRepository.toggleFavorite(plantId)
            result.onSuccess { isFavorite ->
                val message = if (isFavorite) "꽃갈피에 저장되었습니다!" else "꽃갈피에서 제거되었습니다"
                Toast.makeText(this@Browse3Activity, message, Toast.LENGTH_SHORT).show()
            }.onFailure { error ->
                com.example.plant.util.ErrorHandler.handleApiError(this@Browse3Activity, error, "Browse3Activity")
            }
        }
    }
}
