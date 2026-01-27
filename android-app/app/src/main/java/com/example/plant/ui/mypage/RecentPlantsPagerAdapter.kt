package com.example.plant.ui.mypage

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.plant.databinding.ItemMypageRecentPageBinding
import com.example.plant.util.RecentPlantManager.RecentPlant

/**
 * 최근 본 식물 ViewPager2 어댑터 (페이지당 4개 식물)
 */
class RecentPlantsPagerAdapter(
    private val onPlantClick: (RecentPlant) -> Unit
) : RecyclerView.Adapter<RecentPlantsPagerAdapter.PageViewHolder>() {

    private var pages: List<List<RecentPlant>> = emptyList()

    fun submitPages(plants: List<RecentPlant>) {
        // 최대 16개로 제한하고 4개씩 페이지로 분할
        val limitedPlants = plants.take(16)
        pages = limitedPlants.chunked(4)
        notifyDataSetChanged()
    }

    override fun getItemCount(): Int = pages.size

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): PageViewHolder {
        val binding = ItemMypageRecentPageBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return PageViewHolder(binding)
    }

    override fun onBindViewHolder(holder: PageViewHolder, position: Int) {
        holder.bind(pages[position])
    }

    inner class PageViewHolder(
        private val binding: ItemMypageRecentPageBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        private val plantAdapter = MyPageRecentPlantAdapter { plant ->
            onPlantClick(plant)
        }

        init {
            binding.rvPagePlants.apply {
                adapter = plantAdapter
                layoutManager = LinearLayoutManager(context, LinearLayoutManager.HORIZONTAL, false)
            }
        }

        fun bind(plants: List<RecentPlant>) {
            plantAdapter.submitList(plants)
        }
    }
}
