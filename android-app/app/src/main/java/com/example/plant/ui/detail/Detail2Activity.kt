package com.example.plant.ui.detail

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import coil.load
import com.example.plant.R
import com.example.plant.data.remote.dto.response.PlantDetailDto
import com.example.plant.databinding.ActivityDetail2Binding
import com.example.plant.di.AppContainer
import com.example.plant.ui.camera.CameraActivity
import com.example.plant.ui.home.MainActivity
import com.example.plant.ui.bookmark.Bookmark1Activity
import com.example.plant.ui.components.FloripediaBottomBar
import com.example.plant.ui.mypage.MyPageActivity
import kotlinx.coroutines.launch

class Detail2Activity : AppCompatActivity() {

    private lateinit var binding: ActivityDetail2Binding
    private var plantId: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDetail2Binding.inflate(layoutInflater)
        setContentView(binding.root)

        plantId = intent.getStringExtra("plant_id")
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
        binding.btnBack.setOnClickListener { finish() }
        binding.fixedHeader.imgLogo.setOnClickListener {
            val intent = Intent(this, MainActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            startActivity(intent)
        }
    }

    private fun loadPlantDetail(plantId: String) {
        lifecycleScope.launch {
            val result = AppContainer.plantRepository.getPlantDetail(plantId)
            result.onSuccess { plant ->
                displayPlantDetail(plant)
            }
        }
    }

    private fun displayPlantDetail(plant: PlantDetailDto) {
        with(binding) {
            tvFlowerName.text = plant.name

            // 꽃말 태그 표시
            setupFlowerLanguageTags(plant.flowerInfo.language)

            // 이미지 로드
            if (plant.images.isNotEmpty()) {
                ivPlantImage1.load(plant.images[0]) {
                    crossfade(true)
                    placeholder(R.drawable.bg_image_placeholder)
                    error(R.drawable.bg_image_placeholder)
                }
                if (plant.images.size > 1) {
                    ivPlantImage2.visibility = View.VISIBLE
                    ivPlantImage2.load(plant.images[1]) {
                        crossfade(true)
                        placeholder(R.drawable.bg_image_placeholder)
                        error(R.drawable.bg_image_placeholder)
                    }
                } else {
                    ivPlantImage2.visibility = View.GONE
                }
            }

            // 스토리 1
            if (plant.stories.isNotEmpty()) {
                tvFlowerDesc.text = plant.stories[0].content
            }

            // 스토리 2
            if (plant.stories.size >= 2) {
                tvStoryGenre2.visibility = View.VISIBLE
                tvStoryGenre2.text = getStoryGenreKorean(plant.stories[1].genre)
                cvStory2.visibility = View.VISIBLE
                tvStoryContent2.text = plant.stories[1].content
            } else {
                tvStoryGenre2.visibility = View.GONE
                cvStory2.visibility = View.GONE
            }

            // 상세 정보 섹션 바인딩
            val infoSection = detailInfoSection

            // 식물 분류
            infoSection.tvCategoryTitle.text = plant.horticulture.category
            infoSection.tvCategoryDesc.text = plant.horticulture.categoryGroup
            infoSection.ivCategoryImage.setImageResource(getCategoryDrawable(plant.horticulture.categoryGroup))

            // 개화시기
            infoSection.tvSeasonTitle.text = getSeasonKorean(plant.season)
            infoSection.tvSeasonDesc.text = plant.horticulture.management ?: ""
            infoSection.ivSeasonImage.setImageResource(getSeasonDrawable(plant.season))

            // 향기
            val scentTitle = plant.scentInfo.scentTags.joinToString(", ").ifEmpty { "정보 없음" }
            infoSection.tvScentTitle.text = scentTitle
            infoSection.tvScentDesc.text = plant.scentInfo.scentGroup.joinToString(", ")
            infoSection.ivScentImage.setImageResource(getScentDrawable(plant.scentInfo.scentGroup))

            // 색상
            val colorTitle = plant.colorInfo.colorLabels.joinToString(", ").ifEmpty { "정보 없음" }
            infoSection.tvColorTitle.text = colorTitle
            infoSection.tvColorDesc.text = plant.colorInfo.colorGroup.joinToString(", ")
            infoSection.ivColorImage.setImageResource(getColorDrawable(plant.colorInfo.colorGroup))
        }
    }

    private fun getSeasonKorean(season: String): String = when (season.uppercase()) {
        "SPRING" -> "봄"
        "SUMMER" -> "여름"
        "FALL" -> "가을"
        "WINTER" -> "겨울"
        else -> season
    }

    private fun getStoryGenreKorean(genre: String): String = when (genre.uppercase()) {
        "MYTH" -> "신화적 이야기"
        "SCIENCE" -> "과학적 이야기"
        "HISTORY" -> "역사적 이야기"
        else -> genre
    }

    private fun getSeasonDrawable(season: String): Int = when (season.uppercase()) {
        "SPRING" -> R.drawable.spring
        "SUMMER" -> R.drawable.summer
        "FALL" -> R.drawable.autumn
        "WINTER" -> R.drawable.winter
        else -> R.drawable.spring
    }

    private fun getCategoryDrawable(categoryGroup: String): Int {
        val group = categoryGroup.lowercase()
        return when {
            group.contains("구근") -> R.drawable.bulbplant
            group.contains("화초") || group.contains("꽃") -> R.drawable.flower
            group.contains("수목") || group.contains("나무") -> R.drawable.tree
            group.contains("관엽") || group.contains("실내") -> R.drawable.interior
            group.contains("정원") -> R.drawable.garden
            else -> R.drawable.flower
        }
    }

    private fun getScentDrawable(scentGroups: List<String>): Int {
        val scent = scentGroups.joinToString(" ").lowercase()
        return when {
            scent.contains("달콤") || scent.contains("sweet") -> R.drawable.sweet
            scent.contains("상쾌") || scent.contains("시원") || scent.contains("청량") || scent.contains("fresh") -> R.drawable.fresh
            scent.contains("은은") || scent.contains("부드") || scent.contains("가벼") || scent.contains("soft") -> R.drawable.soft
            scent.contains("무향") || scent.contains("없") || scent.isEmpty() -> R.drawable.unscented
            else -> R.drawable.sweet
        }
    }

    private fun getColorDrawable(colorGroups: List<String>): Int {
        val color = colorGroups.joinToString(" ").lowercase()
        return when {
            color.contains("백색") || color.contains("미색") || color.contains("흰") || color.contains("white") -> R.drawable.white
            color.contains("노랑") || color.contains("주황") || color.contains("살구") || color.contains("yellow") || color.contains("orange") -> R.drawable.yellow
            color.contains("빨강") || color.contains("분홍") || color.contains("다홍") || color.contains("red") || color.contains("pink") -> R.drawable.red
            color.contains("파랑") || color.contains("하늘") || color.contains("보라") || color.contains("연보라") || color.contains("푸른") || color.contains("blue") || color.contains("purple") -> R.drawable.blue
            color.contains("갈색") || color.contains("검정") || color.contains("brown") || color.contains("black") -> R.drawable.black
            else -> R.drawable.white
        }
    }

    private fun setupFlowerLanguageTags(flowerLanguage: String) {
        val container = binding.layoutFlowerLanguageTags
        container.removeAllViews()

        if (flowerLanguage.isBlank()) return

        // 쉼표, 슬래시, 공백 등으로 분리
        val tags = flowerLanguage.split(",", "/", "·", "、")
            .map { it.trim() }
            .filter { it.isNotBlank() }

        tags.forEach { tag ->
            val tagView = TextView(this).apply {
                text = "#$tag"
                setTextColor(resources.getColor(R.color.white, null))
                textSize = 13f
                typeface = resources.getFont(R.font.pretendardmedium)
                setBackgroundResource(R.drawable.bg_tag_green)
                setPadding(
                    (14 * resources.displayMetrics.density).toInt(),
                    (8 * resources.displayMetrics.density).toInt(),
                    (14 * resources.displayMetrics.density).toInt(),
                    (8 * resources.displayMetrics.density).toInt()
                )
                val params = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply {
                    marginEnd = (8 * resources.displayMetrics.density).toInt()
                }
                layoutParams = params
            }
            container.addView(tagView)
        }
    }
}
