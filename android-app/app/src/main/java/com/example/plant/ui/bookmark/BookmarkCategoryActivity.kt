package com.example.plant.ui.bookmark

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.PopupMenu
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.GridLayoutManager
import com.example.plant.R
import com.example.plant.data.remote.dto.response.PlantCardDto
import com.example.plant.databinding.ActivityBookmarkCategoryBinding
import com.example.plant.di.AppContainer
import com.example.plant.ui.browse.Browse2Activity
import com.example.plant.ui.camera.CameraActivity
import com.example.plant.ui.components.FloripediaBottomBar
import com.example.plant.ui.detail.Detail1Activity
import com.example.plant.ui.home.MainActivity
import com.example.plant.ui.mypage.MyPageActivity
import kotlinx.coroutines.launch

/**
 * 북마크 카테고리별 식물 목록 화면
 */
class BookmarkCategoryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityBookmarkCategoryBinding
    private lateinit var plantAdapter: BookmarkPlantAdapter
    private var category: String = ""
    private var selectedSubGroup: String = "전체"
    private var sortOrder: String = "desc" // desc = 최신순, asc = 오래된순
    private val subGroupViews = mutableListOf<TextView>()

    // 카테고리별 세부 그룹 정의 (Backend DB 값과 일치해야 함)
    private val subGroupsMap = mapOf(
        "꽃말" to listOf(
            "전체" to null,
            "사랑/고백" to "사랑/고백",
            "위로/슬픔" to "위로/슬픔",
            "감사/존경" to "감사/존경",
            "이별/그리움" to "이별/그리움",
            "행복/즐거움" to "행복/즐거움"
        ),
        "향기" to listOf(
            "전체" to null,
            "달콤·화사" to "달콤·화사",
            "싱그러운·시원" to "싱그러운·시원",
            "은은·차분" to "은은·차분",
            "무향" to "무향"
        ),
        "개화시기" to listOf(
            "전체" to null,
            "봄" to "SPRING",
            "여름" to "SUMMER",
            "가을" to "FALL",
            "겨울" to "WINTER"
        ),
        "색상" to listOf(
            "전체" to null,
            "백색/미색" to "백색/미색",
            "노랑/주황" to "노랑/주황",
            "빨강/분홍" to "빨강/분홍",
            "푸른색" to "푸른색",
            "갈색/검정" to "갈색/검정"
        )
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBookmarkCategoryBinding.inflate(layoutInflater)
        setContentView(binding.root)

        category = intent.getStringExtra("category") ?: "꽃말"

        setupUI()
        setupSubGroupTabs()
        setupRecyclerView()
        setupNavigation()
        loadBookmarkedPlants()
    }

    private fun setupUI() {
        binding.tvTitle.text = category

        binding.btnBack.setOnClickListener {
            finish()
        }

        // 카테고리 드롭다운 클릭
        binding.layoutCategoryDropdown.setOnClickListener {
            showCategoryPopup()
        }

        // 정렬 드롭다운 클릭
        binding.layoutSortDropdown.setOnClickListener {
            showSortPopup()
        }
    }

    private fun setupSubGroupTabs() {
        val subGroups = subGroupsMap[category] ?: listOf("전체" to null)
        binding.layoutSubGroups.removeAllViews()
        subGroupViews.clear()

        subGroups.forEach { (displayName, _) ->
            val textView = TextView(this).apply {
                text = displayName
                textSize = 14f
                typeface = resources.getFont(R.font.pretendardmedium)
                setPadding(32, 16, 32, 16)
                // 리플 효과 없이 흰색 배경만 사용
                background = null
                setBackgroundColor(ContextCompat.getColor(this@BookmarkCategoryActivity, R.color.white))
                isClickable = true
                isFocusable = true
                setOnClickListener { selectSubGroup(displayName) }
            }
            subGroupViews.add(textView)
            binding.layoutSubGroups.addView(textView)
        }

        // 초기 선택 상태
        updateSubGroupSelection()
    }

    private fun selectSubGroup(subGroup: String) {
        selectedSubGroup = subGroup
        updateSubGroupSelection()
        loadBookmarkedPlants() // API 재호출
    }

    private fun updateSubGroupSelection() {
        subGroupViews.forEach { tv ->
            val isSelected = tv.text == selectedSubGroup
            tv.setTextColor(
                ContextCompat.getColor(this, if (isSelected) R.color.text1 else R.color.sub_text1)
            )
            tv.typeface = resources.getFont(
                if (isSelected) R.font.pretendardsemibold else R.font.pretendardmedium
            )
        }
    }

    private fun showCategoryPopup() {
        val popup = PopupMenu(this, binding.layoutCategoryDropdown)
        listOf("꽃말", "향기", "개화시기", "색상").forEach { cat ->
            popup.menu.add(cat)
        }
        popup.setOnMenuItemClickListener { item ->
            category = item.title.toString()
            binding.tvTitle.text = category
            selectedSubGroup = "전체"
            setupSubGroupTabs()
            loadBookmarkedPlants() // API 재호출
            true
        }
        popup.show()
    }

    private fun showSortPopup() {
        val popup = PopupMenu(this, binding.layoutSortDropdown)
        popup.menu.add("최신순")
        popup.menu.add("오래된순")
        popup.setOnMenuItemClickListener { item ->
            binding.tvSortOrder.text = item.title
            sortOrder = if (item.title == "최신순") "desc" else "asc"
            loadBookmarkedPlants() // API 재호출
            true
        }
        popup.show()
    }

    /**
     * 현재 선택된 서브그룹의 API 쿼리 값 반환
     */
    private fun getSelectedSubGroupValue(): String? {
        val subGroups = subGroupsMap[category] ?: return null
        return subGroups.find { it.first == selectedSubGroup }?.second
    }

    private fun displayPlants(plants: List<PlantCardDto>) {
        if (plants.isEmpty()) {
            binding.layoutEmpty.visibility = View.VISIBLE
            binding.rvPlants.visibility = View.GONE
        } else {
            binding.layoutEmpty.visibility = View.GONE
            binding.rvPlants.visibility = View.VISIBLE
        }
        plantAdapter.submitList(plants)
    }

    private fun setupRecyclerView() {
        plantAdapter = BookmarkPlantAdapter { plant ->
            startActivity(Intent(this, Detail1Activity::class.java).apply {
                putExtra("plant_id", plant.id)
            })
        }

        binding.rvPlants.apply {
            adapter = plantAdapter
            layoutManager = GridLayoutManager(this@BookmarkCategoryActivity, 2)
        }
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
                        "search" -> startActivity(Intent(this, Browse2Activity::class.java))
                        "bookmark" -> finish()
                        "my" -> startActivity(Intent(this, MyPageActivity::class.java))
                    }
                },
                onCameraClick = {
                    startActivity(Intent(this, CameraActivity::class.java))
                }
            )
        }
    }

    private fun loadBookmarkedPlants() {
        binding.progressBar.visibility = View.VISIBLE
        binding.layoutEmpty.visibility = View.GONE

        lifecycleScope.launch {
            val subGroupValue = getSelectedSubGroupValue()

            // 디버그 로그
            Log.d("BookmarkCategory", "Loading: category=$category, subGroup=$selectedSubGroup, apiValue=$subGroupValue, sortOrder=$sortOrder")

            // 카테고리별 API 파라미터 설정 (main /plants와 동일한 구조)
            val result = when (category) {
                "꽃말" -> AppContainer.userRepository.getMyFavorites(
                    flowerGroup = subGroupValue,
                    sortBy = "name",
                    sortOrder = sortOrder
                )
                "향기" -> AppContainer.userRepository.getMyFavorites(
                    scentGroup = subGroupValue,
                    sortBy = "name",
                    sortOrder = sortOrder
                )
                "개화시기" -> AppContainer.userRepository.getMyFavorites(
                    season = subGroupValue,
                    sortBy = "name",
                    sortOrder = sortOrder
                )
                "색상" -> AppContainer.userRepository.getMyFavorites(
                    colorGroup = subGroupValue,
                    sortBy = "name",
                    sortOrder = sortOrder
                )
                else -> AppContainer.userRepository.getMyFavorites(
                    sortBy = "name",
                    sortOrder = sortOrder
                )
            }

            binding.progressBar.visibility = View.GONE

            result.onSuccess { plants ->
                Log.d("BookmarkCategory", "API success: ${plants.size} plants loaded")
                displayPlants(plants)
            }.onFailure { error ->
                Log.e("BookmarkCategory", "API error: ${error.message}")
                com.example.plant.util.ErrorHandler.handleAuthRequiredError(
                    this@BookmarkCategoryActivity,
                    error,
                    "BookmarkCategoryActivity"
                )
            }
        }
    }
}
