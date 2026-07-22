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
        // 익명 세션은 앱 시작 시 확보됨 → 별도 로그인 게이트 불필요
        lifecycleScope.launch {
            val result = AppContainer.userRepository.getMyProfile()

            result.onSuccess { user ->
                binding.tvUserName.text = user.nickname

                // @핸들 표시 (email의 @ 앞부분). 익명 세션은 email이 없어 핸들 미표시.
                val email = user.email
                if (!email.isNullOrBlank()) {
                    binding.tvUserHandle.text = "@${email.substringBefore("@")}"
                    binding.tvUserHandle.visibility = View.VISIBLE
                } else {
                    binding.tvUserHandle.visibility = View.GONE
                }

                // 레벨 정보 바인딩
                user.levelInfo?.let { info ->
                    binding.tvLevelTitle.text = getString(R.string.level_title_format, info.title, info.level)
                    // 만렙이면 nextLevelExp=0 → "EXP MAX", 아니면 현재/다음 표시
                    binding.tvExpProgress.text = if (info.nextLevelExp <= 0) {
                        getString(R.string.level_exp_max)
                    } else {
                        getString(R.string.level_exp_format, info.currentLevelExp, info.nextLevelExp)
                    }
                    updateLevelSegments(info.currentLevelExp, info.nextLevelExp)
                    binding.tvDiscoveredCount.text = getString(R.string.discovered_count_format, info.discoveredPlantCount)
                } ?: run {
                    binding.tvLevelTitle.text = getString(R.string.level_title_format, "씨앗", 1)
                    binding.tvExpProgress.text = getString(R.string.level_exp_format, 0, 30)
                    updateLevelSegments(0, 30)
                    binding.tvDiscoveredCount.text = getString(R.string.discovered_count_format, 0)
                }

                // 탐험 기록 (viewedPlantIds 개수 — levelInfo에서 가져올 수 없으므로 discoveredPlantIds 길이 기반)
                binding.tvViewedCount.text = getString(R.string.viewed_count_format, user.discoveredPlantIds.size)

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

    /**
     * 현재 레벨 내 경험치 진행률을 5칸 게이지로 표시 (B 모델).
     * 채운 칸 = round(현재EXP / 다음레벨EXP × 5). 만렙(nextExp<=0)이면 전부 채움.
     */
    private fun updateLevelSegments(currentExp: Int, nextExp: Int) {
        val segments = listOf(
            binding.lvSegment1,
            binding.lvSegment2,
            binding.lvSegment3,
            binding.lvSegment4,
            binding.lvSegment5
        )
        val activeColor = 0xCCFFFFFF.toInt()  // 밝은 흰색
        val inactiveColor = 0x40FFFFFF         // 어두운 반투명

        val filled = if (nextExp <= 0) {
            segments.size
        } else {
            Math.round((currentExp.toFloat() / nextExp) * segments.size).coerceIn(0, segments.size)
        }

        segments.forEachIndexed { index, view ->
            view.setBackgroundColor(if (index < filled) activeColor else inactiveColor)
        }
    }

}
