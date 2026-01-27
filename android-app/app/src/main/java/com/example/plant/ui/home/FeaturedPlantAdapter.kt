package com.example.plant.ui.home

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import coil.load
import com.example.plant.databinding.ItemFeaturedPlantBinding
import com.example.plant.data.remote.dto.response.PlantCardDto

class FeaturedPlantAdapter(
    private val onPlantClick: (PlantCardDto) -> Unit
) : ListAdapter<PlantCardDto, FeaturedPlantAdapter.PlantViewHolder>(PlantDiffCallback()) {

    inner class PlantViewHolder(val binding: ItemFeaturedPlantBinding) :
        androidx.recyclerview.widget.RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): PlantViewHolder {
        val binding = ItemFeaturedPlantBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return PlantViewHolder(binding)
    }

    override fun onBindViewHolder(holder: PlantViewHolder, position: Int) {
        val plant = getItem(position)
        holder.binding.apply {
            tvPlantName.text = plant.name
            // preContent를 설명으로 사용 (story 대신)
            tvDescription.text = plant.preContent ?: ""

            // 꽃말만 태그로 표시 (쉼표로 분리된 경우 처리)
            val flowerLanguages = plant.flowerLanguage.split(",", "、", "/").map { it.trim() }
            if (flowerLanguages.isNotEmpty()) {
                tvTag1.text = "#${flowerLanguages[0]}"
                tvTag1.visibility = android.view.View.VISIBLE
            } else {
                tvTag1.visibility = android.view.View.GONE
            }
            if (flowerLanguages.size > 1) {
                tvTag2.text = "#${flowerLanguages[1]}"
                tvTag2.visibility = android.view.View.VISIBLE
            } else {
                tvTag2.visibility = android.view.View.GONE
            }

            plant.imageUrl?.let { url ->
                ivPlant.load(url) {
                    crossfade(true)
                    placeholder(com.example.plant.R.drawable.bg_image_placeholder)
                    error(com.example.plant.R.drawable.bg_image_placeholder)
                    listener(
                        onError = { _, _ ->
                            ivPlant.setImageResource(com.example.plant.R.drawable.bg_image_placeholder)
                        }
                    )
                }
            } ?: run {
                ivPlant.setImageResource(com.example.plant.R.drawable.bg_image_placeholder)
            }

            // 카드 전체 클릭 리스너
            root.setOnClickListener {
                onPlantClick(plant)
            }
        }
    }

    private class PlantDiffCallback : DiffUtil.ItemCallback<PlantCardDto>() {
        override fun areItemsTheSame(oldItem: PlantCardDto, newItem: PlantCardDto): Boolean {
            return oldItem.id == newItem.id
        }

        override fun areContentsTheSame(oldItem: PlantCardDto, newItem: PlantCardDto): Boolean {
            return oldItem == newItem
        }
    }
}
