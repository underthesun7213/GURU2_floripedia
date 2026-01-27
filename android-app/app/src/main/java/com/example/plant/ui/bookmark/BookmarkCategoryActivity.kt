package com.example.plant.ui.bookmark

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.GridLayoutManager
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

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBookmarkCategoryBinding.inflate(layoutInflater)
        setContentView(binding.root)

        category = intent.getStringExtra("category") ?: "꽃말"

        setupUI()
        setupRecyclerView()
        setupNavigation()
        loadBookmarkedPlants()
    }

    private fun setupUI() {
        binding.tvTitle.text = category

        binding.btnBack.setOnClickListener {
            finish()
        }
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
            val result = AppContainer.userRepository.getMyFavorites()

            binding.progressBar.visibility = View.GONE

            result.onSuccess { plants ->
                if (plants.isEmpty()) {
                    binding.layoutEmpty.visibility = View.VISIBLE
                    binding.rvPlants.visibility = View.GONE
                    binding.tvPlantCount.text = "저장된 식물 0개"
                } else {
                    binding.layoutEmpty.visibility = View.GONE
                    binding.rvPlants.visibility = View.VISIBLE
                    binding.tvPlantCount.text = "저장된 식물 ${plants.size}개"
                    plantAdapter.submitList(plants)
                }
            }.onFailure { error ->
                com.example.plant.util.ErrorHandler.handleAuthRequiredError(
                    this@BookmarkCategoryActivity,
                    error,
                    "BookmarkCategoryActivity"
                )
            }
        }
    }
}
