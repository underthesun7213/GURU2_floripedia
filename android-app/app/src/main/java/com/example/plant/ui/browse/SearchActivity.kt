package com.example.plant.ui.browse

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.plant.databinding.ActivitySearchBinding
import com.example.plant.ui.detail.Detail1Activity
import com.example.plant.util.RecentPlantManager

/**
 * 검색 화면 - 최근 검색 식물 표시
 */
class SearchActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySearchBinding
    private lateinit var recentSearchAdapter: RecentSearchPlantAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySearchBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupUI()
        setupRecyclerView()
        loadRecentSearches()
    }

    private fun setupUI() {
        // 취소 버튼 클릭
        binding.tvCancel.setOnClickListener {
            finish()
        }

        // 검색 실행
        binding.searchView.setOnQueryTextListener(object : androidx.appcompat.widget.SearchView.OnQueryTextListener {
            override fun onQueryTextSubmit(query: String?): Boolean {
                query?.let { performSearch(it) }
                return true
            }

            override fun onQueryTextChange(newText: String?): Boolean {
                return false
            }
        })

        // 검색창 포커스
        binding.searchView.requestFocus()
    }

    private fun setupRecyclerView() {
        recentSearchAdapter = RecentSearchPlantAdapter { plant ->
            // 최근 검색 식물 클릭 시 상세 페이지로 이동
            val intent = Intent(this, Detail1Activity::class.java).apply {
                putExtra("plant_id", plant.id)
            }
            startActivity(intent)
        }

        binding.rvSearchResult.apply {
            adapter = recentSearchAdapter
            layoutManager = LinearLayoutManager(this@SearchActivity)
        }
    }

    private fun loadRecentSearches() {
        val recentPlants = RecentPlantManager.getRecentPlants(this)

        if (recentPlants.isEmpty()) {
            binding.tvRecentSearch.visibility = View.GONE
            binding.rvSearchResult.visibility = View.GONE
        } else {
            binding.tvRecentSearch.visibility = View.VISIBLE
            binding.rvSearchResult.visibility = View.VISIBLE
            recentSearchAdapter.submitList(recentPlants)
        }
    }

    private fun performSearch(keyword: String) {
        if (keyword.trim().isEmpty()) {
            Toast.makeText(this, "검색어를 입력해주세요", Toast.LENGTH_SHORT).show()
            return
        }

        // Browse2Activity로 이동하면서 검색어 전달
        val intent = Intent(this, Browse2Activity::class.java).apply {
            putExtra("search_query", keyword.trim())
        }
        startActivity(intent)
        finish()
    }
}
