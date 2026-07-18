package com.example.plant.ui.detail

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import coil.load
import com.example.plant.R
import com.example.plant.data.remote.dto.response.PlantDetailDto
import com.example.plant.util.loadPlantImage
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
            Toast.makeText(this, getString(R.string.plant_added_to_collection), Toast.LENGTH_LONG).show()
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
                // 삭제된 식물(404): 로컬 최근 본 식물에서도 제거하고 화면 종료
                if (error.message?.contains("404") == true) {
                    com.example.plant.util.RecentPlantManager.removeRecentPlant(this@Detail1Activity, plantId)
                    Toast.makeText(this@Detail1Activity, getString(R.string.plant_not_found), Toast.LENGTH_SHORT).show()
                    finish()
                } else {
                    com.example.plant.util.ErrorHandler.handleApiError(this@Detail1Activity, error, "Detail1Activity")
                }
            }
        }
    }

    private fun displayPlantDetail(plantDetail: PlantDetailDto) {
        plant = plantDetail

        // 최근 본 식물에 이미지와 설명 포함하여 저장
        // 설명은 습니다체인 seasonDescription 우선(horticulture.preContent는 이다체 원전이라 지양)
        val description = plantDetail.seasonDescription?.takeIf { it.isNotBlank() }
            ?: plantDetail.stories.firstOrNull()?.content?.take(50)
            ?: getString(R.string.default_plant_description, plantDetail.name)
        com.example.plant.util.RecentPlantManager.addRecentPlant(
            this,
            plantDetail.id,
            plantDetail.name,
            plantDetail.imageUrl ?: plantDetail.images.firstOrNull(),
            description
        )

        with(binding) {
            tvPlantName.text = plantDetail.name

            // 꽃말 태그 표시
            setupFlowerLanguageTags(plantDetail.flowerInfo.language)

            // 에피소드 1
            if (plantDetail.stories.isNotEmpty()) {
                tvStoryGenre1.visibility = View.VISIBLE
                tvStoryGenre1.text = getStoryGenreKorean(plantDetail.stories[0].genre)
                tvStoryContent1.text = plantDetail.stories[0].content
            } else {
                tvStoryGenre1.visibility = View.GONE
            }

            // 에피소드 2
            if (plantDetail.stories.size >= 2) {
                tvStoryGenre2.visibility = View.VISIBLE
                tvStoryGenre2.text = getStoryGenreKorean(plantDetail.stories[1].genre)
                tvStoryContent2.text = plantDetail.stories[1].content
            } else {
                tvStoryGenre2.visibility = View.GONE
            }

            if (plantDetail.images.isNotEmpty()) {
                tvNoImageHint.visibility = View.GONE
                ivPlantImage1.loadPlantImage(plantDetail.images[0])
                if (plantDetail.images.size > 1) {
                    ivPlantImage2.visibility = View.VISIBLE
                    ivPlantImage2.loadPlantImage(plantDetail.images[1])
                } else {
                    ivPlantImage2.visibility = View.GONE
                }
            } else {
                // 이미지 확정 부재 → 정적 준비중 플레이스홀더 + 제보 안내
                ivPlantImage1.loadPlantImage(null)
                ivPlantImage2.visibility = View.GONE
                tvNoImageHint.visibility = View.VISIBLE
            }

            isFavorite = plantDetail.isFavorite
            updateFavoriteButton()

            // 상세 정보 섹션 바인딩
            val infoSection = detailInfoSection

            // 식물 분류
            infoSection.tvCategoryTitle.text = plantDetail.horticulture.category
            infoSection.tvCategoryDesc.text = plantDetail.horticulture.categoryGroup
            infoSection.ivCategoryImage.setImageResource(getCategoryDrawable(plantDetail.horticulture.categoryGroup))

            // 개화시기
            infoSection.tvSeasonTitle.text = getSeasonKorean(plantDetail.season)
            infoSection.tvSeasonDesc.text = plantDetail.seasonDescription
                ?: plantDetail.horticulture.management ?: ""
            infoSection.ivSeasonImage.setImageResource(getSeasonDrawable(plantDetail.season))

            // 향기
            val scentTitle = plantDetail.scentInfo.scentTags.joinToString(", ").ifEmpty { getString(R.string.info_not_available) }
            infoSection.tvScentTitle.text = scentTitle
            infoSection.tvScentDesc.text = plantDetail.scentInfo.scentGroup.joinToString(", ")
            infoSection.ivScentImage.setImageResource(getScentDrawable(plantDetail.scentInfo.scentGroup))

            // 색상
            val colorTitle = plantDetail.colorInfo.colorLabels.joinToString(", ").ifEmpty { getString(R.string.info_not_available) }
            infoSection.tvColorTitle.text = colorTitle
            infoSection.tvColorDesc.text = plantDetail.colorInfo.colorGroup.joinToString(", ")
            // 칩 이미지는 첫 번째(대표) 색 라벨 기준으로 선택
            infoSection.ivColorImage.setImageResource(getColorDrawable(plantDetail.colorInfo.colorLabels))
        }
    }

    private fun toggleFavorite(plantId: String) {
        lifecycleScope.launch {
            val result = AppContainer.userRepository.toggleFavorite(plantId)
            result.onSuccess { newState ->
                isFavorite = newState
                updateFavoriteButton()
                if (newState) {
                    com.example.plant.util.BookmarkToastUtil.showBookmarkSavedToast(this@Detail1Activity)
                } else {
                    Toast.makeText(this@Detail1Activity, getString(R.string.bookmark_removed), Toast.LENGTH_SHORT).show()
                }
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
                text = getString(R.string.already_in_bookmark)
            } else {
                backgroundTintList = android.content.res.ColorStateList.valueOf(
                    resources.getColor(R.color.button, null)
                )
                text = getString(R.string.save_to_bookmark)
            }
        }
    }

    private fun getSeasonKorean(season: String): String = when (season.uppercase()) {
        "SPRING" -> getString(R.string.season_spring); "SUMMER" -> getString(R.string.season_summer); "FALL" -> getString(R.string.season_fall); "WINTER" -> getString(R.string.season_winter); else -> season
    }

    private fun getStoryGenreKorean(genre: String): String = when (genre.uppercase()) {
        "MYTH" -> getString(R.string.genre_myth); "SCIENCE" -> getString(R.string.genre_science); "HISTORY" -> getString(R.string.genre_history); "ART" -> getString(R.string.genre_art); "EPISODE" -> getString(R.string.genre_episode); else -> genre
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

    /**
     * 색상 칩 이미지 선택.
     * 여러 색을 고정 우선순위로 스캔하면 대표색과 무관한 칩이 뜨므로
     * (예: 첫 색이 분홍이어도 그룹에 백색이 섞이면 흰색 칩),
     * colorLabels의 첫 번째(대표) 색을 기준으로 칩을 고른다.
     * 라벨이 비면 colorGroups로 폴백한다.
     */
    private fun getColorDrawable(colorLabels: List<String>): Int {
        val rep = colorLabels.firstOrNull()?.trim().orEmpty()
        return when {
            rep.contains("초록") || rep.contains("연두") || rep.contains("올리브") -> R.drawable.green
            rep.contains("백색") || rep.contains("미색") || rep.contains("흰") -> R.drawable.white
            rep.contains("노랑") || rep.contains("주황") || rep.contains("살구") -> R.drawable.yellow
            rep.contains("빨강") || rep.contains("분홍") || rep.contains("다홍") || rep.contains("자주") -> R.drawable.red
            rep.contains("파랑") || rep.contains("하늘") || rep.contains("보라") || rep.contains("라일락") || rep.contains("청") -> R.drawable.blue
            rep.contains("갈색") || rep.contains("검정") || rep.contains("은") -> R.drawable.black
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
