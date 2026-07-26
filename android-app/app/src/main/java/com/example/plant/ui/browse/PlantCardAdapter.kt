package com.example.plant.ui.browse

import android.content.Intent
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import coil.load
import com.example.plant.R
import com.example.plant.data.remote.dto.response.PlantCardDto
import com.example.plant.util.loadPlantImage
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
            ivPlantGrid.loadPlantImage(plant.imageUrl)

            // 검색에서 '숨은 키워드'로 매칭된 경우, 왜 나왔는지 근거 칩 표시 (그 외엔 숨김)
            if (!plant.matchReason.isNullOrBlank()) {
                tvMatchReason.text = root.context.getString(R.string.match_reason_format, plant.matchReason)
                tvMatchReason.visibility = android.view.View.VISIBLE
            } else {
                tvMatchReason.visibility = android.view.View.GONE
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
