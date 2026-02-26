package com.example.plant.ui.browse

import android.content.Intent
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import coil.load
import com.example.plant.data.remote.dto.response.PlantCardDto
import com.example.plant.databinding.ItemGridPlantBinding

/**
 * 식물 카드 Adapter (검색 결과 그리드에서 사용)
 */
class PlantCardAdapter(
    private val onPlantClick: (PlantCardDto) -> Unit
) : ListAdapter<PlantCardDto, PlantCardAdapter.PlantCardViewHolder>(PlantCardDiffCallback()) {

    inner class PlantCardViewHolder(val binding: ItemGridPlantBinding) :
        androidx.recyclerview.widget.RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): PlantCardViewHolder {
        val binding = ItemGridPlantBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return PlantCardViewHolder(binding)
    }

    override fun onBindViewHolder(holder: PlantCardViewHolder, position: Int) {
        val plant = getItem(position)
        holder.binding.apply {
            tvPlantGridName.text = plant.name
            plant.imageUrl?.let { url ->
                ivPlantGrid.load(url) {
                    crossfade(true)
                    placeholder(com.example.plant.R.drawable.bg_image_placeholder)
                    error(com.example.plant.R.drawable.bg_image_placeholder)
                }
            } ?: run {
                ivPlantGrid.setImageResource(com.example.plant.R.drawable.bg_image_placeholder)
            }

            // 카드 전체 클릭 리스너
            root.setOnClickListener {
                onPlantClick(plant)
            }
        }
    }

    private class PlantCardDiffCallback : DiffUtil.ItemCallback<PlantCardDto>() {
        override fun areItemsTheSame(oldItem: PlantCardDto, newItem: PlantCardDto): Boolean {
            return oldItem.id == newItem.id
        }

        override fun areContentsTheSame(oldItem: PlantCardDto, newItem: PlantCardDto): Boolean {
            return oldItem == newItem
        }
    }
}
