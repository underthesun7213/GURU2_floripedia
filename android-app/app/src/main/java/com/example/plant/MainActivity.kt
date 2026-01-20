package com.example.plant

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.PagerSnapHelper
import com.example.plant.databinding.ActivityMainBinding
import androidx.recyclerview.widget.RecyclerView

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // --- [기존 하단 바 설정 유지] ---
        binding.bottomNav.background = null
        binding.bottomNav.menu.getItem(2).isEnabled = false

        binding.bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.menu_home -> true
                R.id.menu_search -> true
                R.id.menu_bookmark -> true
                R.id.menu_profile -> true
                else -> false
            }
        }

        binding.fabCamera.setOnClickListener {
            // 카메라 기능 실행
        }

        // --- [기존 슬라이더 및 새로운 스토리 섹션 실행] ---
        val plantData = getSamplePlants() // 데이터를 한 번만 생성해서 재사용합니다.
        setupPlantSlider(plantData)
        setupStorySection(plantData) // 스토리 섹션 추가
        setupAvailablePlantsSection(plantData)

    }

    // 공통으로 사용할 샘플 데이터 생성 함수
    private fun getSamplePlants(): List<Plant> {
        return listOf(
            Plant(
                plantId = "1",
                name = "라일락",
                scientificName = "Syringa vulgaris",
                isRepresentative = true,
                taxonomy = Taxonomy("물푸레나무과", "수수꽃다리속"),
                habitat = "유럽",
                flowerLanguage = "첫사랑",
                story = "유럽 원산으로 전국에 심어 기르는 낙엽 작은키나무입니다. 향기가 매우 진해 첫사랑이라는 꽃말을 가졌습니다.",
                birthDate = listOf("05-12"),
                imageUrl = "https://images.unsplash.com/photo-1599054802207-91d346adc120",
                hexCode = "#B2D8C1",
                season = Season.SPRING,
                bloomingMonths = listOf(4, 5),
                scentTags = listOf("진한향"),
                searchKeywords = listOf("라일락", "보라꽃")
            ),
            Plant(
                plantId = "2",
                name = "수국",
                scientificName = "Hydrangea macrophylla",
                isRepresentative = true,
                taxonomy = Taxonomy("수국과", "수국속"),
                habitat = "동아시아",
                flowerLanguage = "변덕, 진심",
                story = "토양의 산성도에 따라 꽃의 색깔이 변하는 신비로운 꽃입니다. 여름을 대표하는 아름다운 식물입니다.",
                birthDate = listOf("07-13"),
                imageUrl = "https://images.unsplash.com/photo-1501901664534-531ad94477df",
                hexCode = "#A2C2E1",
                season = Season.SUMMER,
                bloomingMonths = listOf(6, 7),
                scentTags = listOf("은은한향"),
                searchKeywords = listOf("수국", "여름꽃")
            )
        )
    }

    private fun setupPlantSlider(samplePlants: List<Plant>) {
        val sliderAdapter = FeaturedPlantAdapter(samplePlants)
        binding.layoutSlider.viewPagerFeatured.adapter = sliderAdapter
        binding.layoutSlider.dotsIndicator.attachTo(binding.layoutSlider.viewPagerFeatured)

        with(binding.layoutSlider.viewPagerFeatured) {
            clipToPadding = false
            clipChildren = false
            offscreenPageLimit = 3
            val offsetPx = (40 * resources.displayMetrics.density).toInt()
            setPadding(offsetPx, 0, offsetPx, 0)
            val marginPx = (20 * resources.displayMetrics.density).toInt()
            setPageTransformer { page, position ->
                page.translationX = -marginPx * position
            }
        }
    }

    // --- [새로 추가된 스토리 섹션 설정] ---
    // 1. 스토리 섹션 (인디케이터 포함)
    private fun setupStorySection(samplePlants: List<Plant>) {
        val storyAdapter = StoryAdapter(samplePlants)
        val layoutManager = LinearLayoutManager(this, LinearLayoutManager.HORIZONTAL, false)

        binding.layoutStories.rvStories.apply {
            this.adapter = storyAdapter
            this.layoutManager = layoutManager

            val snapHelper = PagerSnapHelper()
            if (onFlingListener == null) snapHelper.attachToRecyclerView(this)

            // 인디케이터 에러 해결을 위해 리스너 수동 구현
            addOnScrollListener(object : RecyclerView.OnScrollListener() {
                override fun onScrollStateChanged(recyclerView: RecyclerView, newState: Int) {
                    super.onScrollStateChanged(recyclerView, newState)
                    if (newState == RecyclerView.SCROLL_STATE_IDLE) {
                        val centerView = snapHelper.findSnapView(layoutManager)
                        val pos = centerView?.let { layoutManager.getPosition(it) } ?: 0
                        // 여기서 setDotSelection 에러가 계속 나면 라이브러리가 지원하지 않는 것이니 주석처리 하세요.
                        // binding.layoutStories.storyDotsIndicator.setDotSelection(pos)
                    }
                }
            })
        }
    }

    // 2. 가용 식물 섹션 (슬라이드만 가능, 점 없음)
    private fun setupAvailablePlantsSection(samplePlants: List<Plant>) {
        // 바뀐 이름의 어댑터를 사용합니다.
        val availableAdapter = AvailablePlantAdapter(samplePlants)

        binding.layoutAvailable.rvAvailablePlants.apply {
            this.adapter = availableAdapter
            this.layoutManager = LinearLayoutManager(this@MainActivity, LinearLayoutManager.HORIZONTAL, false)

            // 점 없이 슬라이드만 되도록 설정
            val snapHelper = PagerSnapHelper()
            if (onFlingListener == null) snapHelper.attachToRecyclerView(this)
        }
    }
}