package com.example.plant.ui.home

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.runtime.*
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.plant.R
import com.example.plant.databinding.ActivityMainBinding
import com.example.plant.di.AppContainer
import com.example.plant.data.remote.TokenManager
import com.example.plant.ui.camera.CameraActivity
import com.example.plant.ui.browse.Browse2Activity
import com.example.plant.ui.bookmark.Bookmark1Activity
import com.example.plant.ui.mypage.MyPageActivity
import com.example.plant.data.model.FilterCategory
import com.example.plant.data.model.FilterType
import com.example.plant.data.model.FilterCategoryFactory
import com.example.plant.ui.detail.Detail1Activity
import com.example.plant.util.ErrorHandler
import com.example.plant.ui.components.FloripediaBottomBar
import com.example.plant.ui.components.FloripediaCategorySection
import com.google.android.gms.ads.AdLoader
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.nativead.NativeAd
import com.google.android.gms.ads.nativead.NativeAdView
import com.example.plant.BuildConfig
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private var currentFilter: FilterState = FilterState.None
    
    // Compose 상태를 관리하기 위한 MutableState
    private val subCategoriesState = mutableStateListOf<FilterCategory>()
    private var selectedTopIndexState = mutableIntStateOf(0)

    private sealed class FilterState {
        object None : FilterState()
        data class Season(val season: String) : FilterState()
        data class CategoryGroup(val group: String) : FilterState()
        data class ColorGroup(val group: String) : FilterState()
        data class ScentGroup(val group: String) : FilterState()
        data class FlowerGroup(val group: String) : FilterState()
        data class StoryGenre(val genre: String) : FilterState()
    }

    private lateinit var featuredAdapter: FeaturedPlantAdapter
    private lateinit var availableAdapter: AvailablePlantAdapter
    private lateinit var storyAdapter: StoryAdapter
    private var currentNativeAd: NativeAd? = null
    private var allFilterCategories: MutableList<FilterCategory> = mutableListOf()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // 익명 세션 보장(로그인 화면 없이 uid/토큰 확보) + 토큰 갱신
        ensureSession()

        // 로그인 상태 확인 없이 앱 시작 - 인증 필요 시 ErrorHandler가 리다이렉트 처리
        allFilterCategories = FilterCategoryFactory.createDefaultFilters().toMutableList()
        updateFilteredSubCategories(0) // 초기화

        setupNavigation()
        setupCategoryCompose()
        setupAdapters()
        setupSearchBar()

        loadFeaturedPlants()
        loadPopularStories()
        loadAvailablePlants()
        loadBannerAd()
    }

    /**
     * 익명 세션 보장 + 토큰 갱신.
     * 로그인돼 있지 않으면 익명 로그인으로 세션을 만들고 백엔드 유저 문서를 생성한다.
     */
    private fun ensureSession() {
        lifecycleScope.launch {
            com.example.plant.data.auth.SessionManager.ensureSession(applicationContext)
        }
    }

    private fun setupSearchBar() {
        val etSearch = findViewById<android.widget.EditText>(R.id.etSearch)

        // 검색창 클릭 시 SearchActivity로 이동
        etSearch?.setOnClickListener {
            startActivity(Intent(this, com.example.plant.ui.browse.SearchActivity::class.java))
        }

        // 검색창 포커스 시에도 SearchActivity로 이동
        etSearch?.setOnFocusChangeListener { _, hasFocus ->
            if (hasFocus) {
                etSearch.clearFocus()
                startActivity(Intent(this, com.example.plant.ui.browse.SearchActivity::class.java))
            }
        }

        // 검색 아이콘 클릭 시 검색 화면으로 이동
        findViewById<android.widget.ImageView>(R.id.ivSearchIcon)?.setOnClickListener {
            startActivity(Intent(this, com.example.plant.ui.browse.SearchActivity::class.java))
        }
    }

    private fun setupNavigation() {
        // 헤더의 마이페이지 아이콘 클릭
        binding.fixedHeader.imgUser.setOnClickListener {
            startActivity(Intent(this, MyPageActivity::class.java))
        }

        binding.bottomNav.composeViewBottomNav.setContent {
            FloripediaBottomBar(
                selectedMenu = "home",
                onNavigate = { menu ->
                    when (menu) {
                        "home" -> binding.scrollView.smoothScrollTo(0, 0)
                        "search" -> startActivity(Intent(this, Browse2Activity::class.java))
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

    private fun setupCategoryCompose() {
        binding.layoutCategoryTab.composeViewCategory.setContent {
            val topCategories = listOf(
                getString(R.string.category_blooming_season),
                getString(R.string.category_flower_language),
                getString(R.string.category_scent),
                getString(R.string.category_plant_classification),
                getString(R.string.category_color)
            )
            
            FloripediaCategorySection(
                topCategories = topCategories,
                selectedTopIndex = selectedTopIndexState.intValue,
                onTopCategoryClick = { index -> 
                    selectedTopIndexState.intValue = index
                    updateFilteredSubCategories(index)
                },
                subCategories = subCategoriesState,
                onSubCategoryClick = { category ->
                    handleFilterClick(category)
                    updateFilteredSubCategories(selectedTopIndexState.intValue)
                }
            )
        }
    }

    private fun updateFilteredSubCategories(index: Int) {
        val currentType = when (index) {
            0 -> FilterType.SEASON
            1 -> FilterType.FLOWER_GROUP
            2 -> FilterType.SCENT_GROUP
            3 -> FilterType.CATEGORY_GROUP
            else -> FilterType.COLOR_GROUP
        }
        subCategoriesState.clear()
        subCategoriesState.addAll(allFilterCategories.filter { it.filterType == currentType })
    }

    private fun handleFilterClick(category: FilterCategory) {
        val targetValue = category.filterValue
        val wasSelected = category.isSelected

        allFilterCategories.forEachIndexed { index, filter ->
            if (filter.filterType == category.filterType) {
                allFilterCategories[index] = filter.copy(isSelected = (filter.filterValue == targetValue && !wasSelected))
            } else {
                allFilterCategories[index] = filter.copy(isSelected = false)
            }
        }

        val selected = allFilterCategories.find { it.isSelected }
        currentFilter = if (selected != null) {
            when (selected.filterType) {
                FilterType.SEASON -> FilterState.Season(selected.filterValue)
                FilterType.CATEGORY_GROUP -> FilterState.CategoryGroup(selected.filterValue)
                FilterType.COLOR_GROUP -> FilterState.ColorGroup(selected.filterValue)
                FilterType.SCENT_GROUP -> FilterState.ScentGroup(selected.filterValue)
                FilterType.FLOWER_GROUP -> FilterState.FlowerGroup(selected.filterValue)
                FilterType.STORY_GENRE -> FilterState.StoryGenre(selected.filterValue)
                else -> FilterState.None
            }
        } else {
            FilterState.None
        }

        loadFeaturedPlants()
    }

    private fun loadFeaturedPlants() {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            val result = when (val filter = currentFilter) {
                is FilterState.Season -> AppContainer.plantRepository.getPlants(season = filter.season, limit = 5)
                is FilterState.CategoryGroup -> AppContainer.plantRepository.getPlants(categoryGroup = filter.group, limit = 5)
                is FilterState.ColorGroup -> AppContainer.plantRepository.getPlants(colorGroup = filter.group, limit = 5)
                is FilterState.ScentGroup -> AppContainer.plantRepository.getPlants(scentGroup = filter.group, limit = 5)
                is FilterState.FlowerGroup -> AppContainer.plantRepository.getPlants(flowerGroup = filter.group, limit = 5)
                is FilterState.StoryGenre -> AppContainer.plantRepository.getPlants(storyGenre = filter.genre, limit = 5)
                else -> AppContainer.plantRepository.getPlants(sortBy = "popularity_score", limit = 5)
            }
            binding.progressBar.visibility = View.GONE
            result.onSuccess { plants ->
                // 이미지가 준비된 식물만 표시
                val plantsWithImages = plants.filter { !it.imageUrl.isNullOrEmpty() }
                featuredAdapter.submitList(plantsWithImages)
            }.onFailure { error ->
                ErrorHandler.handleApiError(this@MainActivity, error, "MainActivity_Featured")
            }
        }
    }

    private fun setupAdapters() {
        featuredAdapter = FeaturedPlantAdapter { plant ->
            startActivity(Intent(this, Detail1Activity::class.java).apply { putExtra("plant_id", plant.id) })
        }
        binding.layoutSlider.viewPagerFeatured.apply {
            adapter = featuredAdapter
            // 양옆 인접 카드가 살짝 보이게(peek) - 넘길 수 있음을 시각적으로 표현.
            // ViewPager2 함정: clipToPadding/offscreen을 내부 RecyclerView에도 적용해야 peek이 렌더됨.
            offscreenPageLimit = 3
            (getChildAt(0) as? androidx.recyclerview.widget.RecyclerView)?.apply {
                clipToPadding = false
                clipChildren = false
            }
            // 히어로 캐러셀: 가운데 카드 강조, 양옆 인접 카드는 0.69배로 축소(시안 300dp→208dp 측정).
            // pivot을 '중심 쪽 가장자리'로 둬서 축소해도 peek(가장자리)이 유지되게 함.
            setPageTransformer { page, position ->
                val minScale = 0.69f
                val absPos = kotlin.math.abs(position).coerceIn(0f, 1f)
                val scale = minScale + (1f - minScale) * (1f - absPos)
                page.pivotY = page.height / 2f
                page.pivotX = when {
                    position < 0f -> page.width.toFloat()  // 왼쪽 카드: 오른쪽(중심측) 가장자리 기준
                    position > 0f -> 0f                     // 오른쪽 카드: 왼쪽(중심측) 가장자리 기준
                    else -> page.width / 2f
                }
                page.scaleX = scale
                page.scaleY = scale
                // 사이드(비중앙) 카드는 내용 숨겨 빈 카드로 - 중앙일 때만 이미지·글씨 표시
                page.findViewById<android.view.View>(R.id.featuredContent)?.alpha =
                    (1f - absPos).coerceIn(0f, 1f)
            }
        }
        binding.layoutSlider.dotsIndicator.attachTo(binding.layoutSlider.viewPagerFeatured)

        storyAdapter = StoryAdapter { story ->
            startActivity(Intent(this, Detail1Activity::class.java).apply { putExtra("plant_id", story.plantId) })
        }
        binding.layoutStorySection.rvStories.apply {
            adapter = storyAdapter
            layoutManager = LinearLayoutManager(this@MainActivity, LinearLayoutManager.HORIZONTAL, false)
        }

        availableAdapter = AvailablePlantAdapter { plant ->
            startActivity(Intent(this, Detail1Activity::class.java).apply { putExtra("plant_id", plant.id) })
        }
        binding.layoutAvailable.rvAvailablePlants.apply {
            adapter = availableAdapter
            layoutManager = LinearLayoutManager(this@MainActivity, LinearLayoutManager.HORIZONTAL, false)
        }
    }

    private fun loadPopularStories() {
        lifecycleScope.launch {
            AppContainer.plantRepository.getPopularStories(limit = 10)
                .onSuccess { stories ->
                    val storiesWithImages = stories.filter { !it.imageUrl.isNullOrEmpty() }
                    storyAdapter.submitList(storiesWithImages)
                }
                .onFailure { error ->
                    ErrorHandler.handleApiError(this@MainActivity, error, "MainActivity_Stories")
                }
        }
    }

    private fun loadAvailablePlants() {
        lifecycleScope.launch {
            val currentMonth = java.util.Calendar.getInstance().get(java.util.Calendar.MONTH) + 1
            AppContainer.plantRepository.getPlants(bloomingMonth = currentMonth, limit = 10)
                .onSuccess { plants ->
                    // 이미지가 준비된 식물만 표시 (최대 5개)
                    val plantsWithImages = plants.filter { !it.imageUrl.isNullOrEmpty() }.take(5)
                    availableAdapter.submitList(plantsWithImages)
                }
                .onFailure { error ->
                    ErrorHandler.handleApiError(this@MainActivity, error, "MainActivity_Available")
                }
        }
    }

    private fun loadBannerAd() {
        val adLoader = AdLoader.Builder(this, BuildConfig.ADMOB_BANNER_ID)
            .forNativeAd { nativeAd ->
                currentNativeAd?.destroy()
                currentNativeAd = nativeAd

                val adView = layoutInflater.inflate(
                    R.layout.item_native_ad, null
                ) as NativeAdView

                populateNativeAdView(nativeAd, adView)

                binding.nativeAdContainer.removeAllViews()
                binding.nativeAdContainer.addView(adView)
            }
            .build()

        adLoader.loadAd(AdRequest.Builder().build())
    }

    private fun populateNativeAdView(nativeAd: NativeAd, adView: NativeAdView) {
        val headlineView = adView.findViewById<android.widget.TextView>(R.id.adHeadline)
        val bodyView = adView.findViewById<android.widget.TextView>(R.id.adBody)
        val iconView = adView.findViewById<android.widget.ImageView>(R.id.adIcon)
        val mediaView = adView.findViewById<com.google.android.gms.ads.nativead.MediaView>(R.id.adMedia)
        val ctaView = adView.findViewById<android.widget.TextView>(R.id.adCallToAction)
        val advertiserView = adView.findViewById<android.widget.TextView>(R.id.adAdvertiser)

        adView.headlineView = headlineView
        adView.bodyView = bodyView
        adView.iconView = iconView
        adView.mediaView = mediaView
        adView.callToActionView = ctaView
        adView.advertiserView = advertiserView

        headlineView.text = nativeAd.headline
        bodyView.text = nativeAd.body
        ctaView.text = nativeAd.callToAction

        if (nativeAd.icon != null) {
            iconView.setImageDrawable(nativeAd.icon!!.drawable)
            iconView.visibility = View.VISIBLE
        } else {
            iconView.visibility = View.GONE
        }

        if (nativeAd.advertiser != null) {
            advertiserView.text = nativeAd.advertiser
            advertiserView.visibility = View.VISIBLE
        } else {
            advertiserView.visibility = View.GONE
        }

        adView.setNativeAd(nativeAd)
    }

    override fun onDestroy() {
        currentNativeAd?.destroy()
        super.onDestroy()
    }

}
