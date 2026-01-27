package com.example.plant.ui.mypage

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.viewpager2.widget.ViewPager2
import coil.load
import com.example.plant.R
import com.example.plant.databinding.ActivityMypageBinding
import com.example.plant.di.AppContainer
import com.example.plant.ui.auth.LoginActivity
import com.example.plant.ui.home.MainActivity
import com.example.plant.ui.bookmark.Bookmark1Activity
import com.example.plant.ui.browse.Browse2Activity
import com.example.plant.ui.camera.CameraActivity
import com.example.plant.ui.components.FloripediaBottomBar
import com.example.plant.ui.detail.Detail1Activity
import com.example.plant.util.RecentPlantManager
import kotlinx.coroutines.launch

/**
 * 마이페이지 화면
 */
class MyPageActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMypageBinding
    private lateinit var recentPagerAdapter: RecentPlantsPagerAdapter
    private var totalPages = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMypageBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupUI()
        setupRecentPlantsViewPager()
        loadUserProfile()
        loadRecentPlants()
    }

    override fun onResume() {
        super.onResume()
        loadRecentPlants()
    }

    private fun setupUI() {
        // 프로필 수정 버튼
        binding.btnEditProfile.setOnClickListener {
            startActivity(Intent(this, ProfileEditActivity::class.java))
        }

        // 컴포즈 푸터바 설정
        binding.bottomNav.composeViewBottomNav.setContent {
            FloripediaBottomBar(
                selectedMenu = "my",
                onNavigate = { menu ->
                    when (menu) {
                        "home" -> {
                            val intent = Intent(this, MainActivity::class.java)
                            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
                            startActivity(intent)
                        }
                        "search" -> {
                            startActivity(Intent(this, Browse2Activity::class.java))
                        }
                        "bookmark" -> {
                            startActivity(Intent(this, Bookmark1Activity::class.java))
                        }
                    }
                },
                onCameraClick = {
                    startActivity(Intent(this, CameraActivity::class.java))
                }
            )
        }
    }

    private fun setupRecentPlantsViewPager() {
        recentPagerAdapter = RecentPlantsPagerAdapter { plant ->
            // 최근 본 식물 클릭 시 상세 페이지로 이동
            startActivity(Intent(this, Detail1Activity::class.java).apply {
                putExtra("plant_id", plant.id)
            })
        }

        binding.vpRecentPlants.apply {
            adapter = recentPagerAdapter
            registerOnPageChangeCallback(object : ViewPager2.OnPageChangeCallback() {
                override fun onPageSelected(position: Int) {
                    updateSlideIndicator(position)
                }
            })
        }
    }

    private fun loadRecentPlants() {
        val recentPlants = RecentPlantManager.getRecentPlants(this)

        if (recentPlants.isEmpty()) {
            binding.vpRecentPlants.visibility = View.GONE
            binding.tvNoRecentPlants.visibility = View.VISIBLE
            binding.slideIndicator.visibility = View.GONE
        } else {
            binding.vpRecentPlants.visibility = View.VISIBLE
            binding.tvNoRecentPlants.visibility = View.GONE
            binding.slideIndicator.visibility = View.VISIBLE

            // 최대 16개로 제한
            val limitedPlants = recentPlants.take(16)
            recentPagerAdapter.submitPages(limitedPlants)

            // 페이지 수 계산 (4개씩, 최대 4페이지)
            totalPages = calculatePageCount(limitedPlants.size)

            // 슬라이드 인디케이터 초기화
            setupSlideIndicator(totalPages)
            updateSlideIndicator(0)
        }
    }

    /**
     * 페이지 수 계산
     * - count / 4로 나누어 떨어지면 그 몫 (최대 4)
     * - 나누어 떨어지지 않으면 몫 + 1 (최대 4)
     */
    private fun calculatePageCount(plantCount: Int): Int {
        if (plantCount == 0) return 0
        val quotient = plantCount / 4
        val remainder = plantCount % 4
        val pages = if (remainder == 0) quotient else quotient + 1
        return minOf(pages, 4)
    }

    private fun setupSlideIndicator(pageCount: Int) {
        val indicators = listOf(
            binding.indicator1,
            binding.indicator2,
            binding.indicator3,
            binding.indicator4
        )

        // 필요한 인디케이터만 표시
        indicators.forEachIndexed { index, indicator ->
            indicator.visibility = if (index < pageCount) View.VISIBLE else View.GONE
        }
    }

    private fun updateSlideIndicator(currentPage: Int) {
        val indicators = listOf(
            binding.indicator1,
            binding.indicator2,
            binding.indicator3,
            binding.indicator4
        )

        val activeColor = resources.getColor(R.color.button, null)
        val inactiveColor = resources.getColor(R.color.chip, null)

        indicators.forEachIndexed { index, indicator ->
            if (indicator.visibility == View.VISIBLE) {
                // 좌측이 최신이므로 currentPage와 index가 같으면 active
                indicator.setBackgroundColor(if (index == currentPage) activeColor else inactiveColor)
            }
        }
    }

    private fun loadUserProfile() {
        // 로그인 상태 확인
        if (!AppContainer.firebaseAuthManager.isLoggedIn()) {
            navigateToLogin()
            return
        }

        lifecycleScope.launch {
            val result = AppContainer.userRepository.getMyProfile()

            result.onSuccess { user ->
                binding.tvUserName.text = user.nickname

                user.profileImageUrl?.let { url ->
                    binding.ivProfile.load(url) {
                        crossfade(true)
                        placeholder(R.drawable.ic_profile_placeholder)
                        error(R.drawable.ic_profile_placeholder)
                    }
                } ?: run {
                    binding.ivProfile.setImageResource(R.drawable.ic_profile_placeholder)
                }
            }.onFailure { error ->
                // 인증 에러 시 로그인 화면으로 리다이렉트
                com.example.plant.util.ErrorHandler.handleAuthRequiredError(
                    this@MyPageActivity,
                    error,
                    "MyPageActivity"
                )
            }
        }
    }

    private fun navigateToLogin() {
        val intent = Intent(this, LoginActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }
}
