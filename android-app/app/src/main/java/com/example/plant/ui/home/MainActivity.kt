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
    private var allFilterCategories: MutableList<FilterCategory> = mutableListOf()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Firebase 로그인 상태이면 토큰 갱신
        refreshTokenIfLoggedIn()

        // 로그인 상태 확인 없이 앱 시작 - 인증 필요 시 ErrorHandler가 리다이렉트 처리
        allFilterCategories = FilterCategoryFactory.createDefaultFilters().toMutableList()
        updateFilteredSubCategories(0) // 초기화

        setupNavigation()
        setupCategoryCompose()
        setupAdapters()
        setupSearchBar()

        loadFeaturedPlants()
        loadAvailablePlants()
    }

    /**
     * Firebase에 로그인되어 있으면 ID Token 갱신
     */
    private fun refreshTokenIfLoggedIn() {
        if (AppContainer.firebaseAuthManager.isLoggedIn()) {
            lifecycleScope.launch {
                val newToken = AppContainer.firebaseAuthManager.getIdToken()
                if (newToken != null) {
                    TokenManager.setToken(newToken, applicationContext)
                }
            }
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
            val topCategories = listOf("개화시기", "꽃말", "향기", "식물분류", "색상")
            
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
        binding.layoutSlider.viewPagerFeatured.adapter = featuredAdapter
        binding.layoutSlider.dotsIndicator.attachTo(binding.layoutSlider.viewPagerFeatured)

        availableAdapter = AvailablePlantAdapter { plant ->
            startActivity(Intent(this, Detail1Activity::class.java).apply { putExtra("plant_id", plant.id) })
        }
        binding.layoutAvailable.rvAvailablePlants.apply {
            adapter = availableAdapter
            layoutManager = LinearLayoutManager(this@MainActivity, LinearLayoutManager.HORIZONTAL, false)
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

}
