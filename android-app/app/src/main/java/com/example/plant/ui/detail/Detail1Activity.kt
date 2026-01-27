package com.example.plant.ui.detail

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import coil.load
import com.example.plant.R
import com.example.plant.data.remote.dto.response.PlantDetailDto
import com.example.plant.databinding.ActivityDetail1Binding
import com.example.plant.di.AppContainer
import com.example.plant.ui.camera.CameraActivity
import com.example.plant.ui.bookmark.Bookmark1Activity
import com.example.plant.ui.home.MainActivity
import com.example.plant.ui.components.FloripediaBottomBar
import com.example.plant.ui.mypage.MyPageActivity
import kotlinx.coroutines.launch

class Detail1Activity : AppCompatActivity() {

    private lateinit var binding: ActivityDetail1Binding
    private var plantId: String? = null
    private var isFavorite: Boolean = false
    private var plant: PlantDetailDto? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDetail1Binding.inflate(layoutInflater)
        setContentView(binding.root)

        plantId = intent.getStringExtra("plant_id")
        val isNewlyCreated = intent.getBooleanExtra("is_newly_created", false)

        if (isNewlyCreated) {
            Toast.makeText(this, "새로운 식물이 도감에 추가되었습니다!", Toast.LENGTH_LONG).show()
        }

        setupNavigation()
        setupUI()
        plantId?.let { loadPlantDetail(it) }
    }

    private fun setupNavigation() {
        binding.bottomNav.composeViewBottomNav.setContent {
            FloripediaBottomBar(
                selectedMenu = "home",
                onNavigate = { menu ->
                    when (menu) {
                        "home" -> {
                            val intent = Intent(this, MainActivity::class.java)
                            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
                            startActivity(intent)
                        }
                        "search" -> startActivity(Intent(this, com.example.plant.ui.browse.Browse2Activity::class.java))
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
        binding.btnBookmark.setOnClickListener {
            plantId?.let { toggleFavorite(it) }
        }

        binding.fixedHeader.imgLogo.setOnClickListener {
            val intent = Intent(this, MainActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            startActivity(intent)
        }

        // 마이페이지 아이콘 클릭 리스너 추가
        binding.fixedHeader.imgUser.setOnClickListener {
            val intent = Intent(this, MyPageActivity::class.java)
            startActivity(intent)
        }

        binding.btnBack.setOnClickListener {
            finish()
        }
    }

    private fun loadPlantDetail(plantId: String) {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            val result = AppContainer.plantRepository.getPlantDetail(plantId)
            binding.progressBar.visibility = View.GONE
            result.onSuccess { displayPlantDetail(it) }.onFailure { error ->
                com.example.plant.util.ErrorHandler.handleApiError(this@Detail1Activity, error, "Detail1Activity")
            }
        }
    }

    private fun displayPlantDetail(plantDetail: PlantDetailDto) {
        plant = plantDetail

        // 최근 본 식물에 이미지와 설명 포함하여 저장
        val description = plantDetail.horticulture.preContent
            ?: plantDetail.stories.firstOrNull()?.content?.take(50)
            ?: "${plantDetail.name}은 아름다운 식물입니다"
        com.example.plant.util.RecentPlantManager.addRecentPlant(
            this,
            plantDetail.id,
            plantDetail.name,
            plantDetail.imageUrl ?: plantDetail.images.firstOrNull(),
            description
        )

        with(binding) {
            tvPlantName.text = plantDetail.name
            
            // 에피소드 1
            if (plantDetail.stories.size >= 1) {
                tvStoryGenre1.visibility = View.VISIBLE
                tvStoryGenre1.text = "[${getStoryGenreKorean(plantDetail.stories[0].genre)}]"
                tvStoryContent1.text = plantDetail.stories[0].content
            } else {
                tvStoryGenre1.visibility = View.GONE
            }

            // 에피소드 2
            if (plantDetail.stories.size >= 2) {
                tvStoryGenre2.visibility = View.VISIBLE
                tvStoryGenre2.text = "[${getStoryGenreKorean(plantDetail.stories[1].genre)}]"
                tvStoryContent2.text = plantDetail.stories[1].content
            } else {
                tvStoryGenre2.visibility = View.GONE
            }

            if (plantDetail.images.isNotEmpty()) {
                ivPlantImage1.load(plantDetail.images[0]) {
                    crossfade(true)
                    placeholder(R.drawable.bg_image_placeholder)
                    error(R.drawable.bg_image_placeholder)
                }
                if (plantDetail.images.size > 1) {
                    ivPlantImage2.visibility = View.VISIBLE
                    ivPlantImage2.load(plantDetail.images[1]) {
                        crossfade(true)
                        placeholder(R.drawable.bg_image_placeholder)
                        error(R.drawable.bg_image_placeholder)
                    }
                } else {
                    ivPlantImage2.visibility = View.GONE
                }
            } else {
                ivPlantImage1.setImageResource(R.drawable.bg_image_placeholder)
                ivPlantImage2.visibility = View.GONE
            }

            isFavorite = plantDetail.isFavorite
            updateFavoriteButton()
        }
    }

    private fun toggleFavorite(plantId: String) {
        lifecycleScope.launch {
            val result = AppContainer.userRepository.toggleFavorite(plantId)
            result.onSuccess { newState ->
                isFavorite = newState
                updateFavoriteButton()
                Toast.makeText(this@Detail1Activity, if (newState) "저장되었습니다!" else "제거되었습니다", Toast.LENGTH_SHORT).show()
            }.onFailure { error ->
                com.example.plant.util.ErrorHandler.handleAuthRequiredError(
                    this@Detail1Activity,
                    error,
                    "Detail1Activity"
                )
            }
        }
    }

    private fun updateFavoriteButton() {
        with(binding.btnBookmark) {
            if (isFavorite) {
                backgroundTintList = android.content.res.ColorStateList.valueOf(
                    resources.getColor(R.color.sub_text1, null)
                )
                text = "이미 꽃갈피에 있어요"
            } else {
                backgroundTintList = android.content.res.ColorStateList.valueOf(
                    resources.getColor(R.color.button, null)
                )
                text = "꽃갈피에 저장"
            }
        }
    }

    private fun getSeasonKorean(season: String): String = when (season.uppercase()) {
        "SPRING" -> "봄"; "SUMMER" -> "여름"; "FALL" -> "가을"; "WINTER" -> "겨울"; else -> season
    }

    private fun getStoryGenreKorean(genre: String): String = when (genre.uppercase()) {
        "MYTH" -> "신화"; "SCIENCE" -> "과학"; "HISTORY" -> "역사"; else -> genre
    }
}
