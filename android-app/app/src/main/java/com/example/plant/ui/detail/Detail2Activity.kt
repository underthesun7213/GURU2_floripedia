package com.example.plant.ui.detail

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import coil.load
import com.example.plant.R
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
        // Detail2Activity에는 progressBar가 없으므로 해당 코드 제거 또는 safe call 사용
        lifecycleScope.launch {
            val result = AppContainer.plantRepository.getPlantDetail(plantId)
            result.onSuccess { plant ->
                binding.tvFlowerName.text = plant.name
                binding.ivPlantImage1.load(plant.images.getOrNull(0)) {
                    placeholder(R.drawable.rose)
                }
            }
        }
    }
}
