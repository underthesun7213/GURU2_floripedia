package com.example.plant.ui.home

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import coil.load
import com.example.plant.databinding.ItemAvailablePlantBinding
import com.example.plant.util.loadPlantImage
import com.example.plant.data.remote.dto.response.PlantCardDto

class AvailablePlantAdapter(
    private val onPlantClick: (PlantCardDto) -> Unit
) : ListAdapter<PlantCardDto, AvailablePlantAdapter.ViewHolder>(PlantDiffCallback()) {

    inner class ViewHolder(val binding: ItemAvailablePlantBinding) :
        androidx.recyclerview.widget.RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemAvailablePlantBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val plant = getItem(position)
        holder.binding.apply {
            tvPlantGridName.text = plant.name

            // 꽃말을 태그로 표시 (첫 번째 꽃말만, 없으면 숨김)
            val flower = plant.flowerLanguage.split(",", "、", "/").firstOrNull()?.trim()
            if (!flower.isNullOrEmpty()) {
                tvPlantGridTag.text = "#$flower"
                tvPlantGridTag.visibility = android.view.View.VISIBLE
            } else {
                tvPlantGridTag.visibility = android.view.View.GONE
            }

            ivPlantGrid.loadPlantImage(plant.imageUrl)

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
