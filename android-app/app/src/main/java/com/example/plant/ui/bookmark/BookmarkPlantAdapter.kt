package com.example.plant.ui.bookmark

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import coil.load
import com.example.plant.R
import com.example.plant.data.remote.dto.response.PlantCardDto
import com.example.plant.databinding.ItemBookmarkPlantBinding

class BookmarkPlantAdapter(
    private val onItemClick: (PlantCardDto) -> Unit
) : ListAdapter<PlantCardDto, BookmarkPlantAdapter.ViewHolder>(DiffCallback()) {

    inner class ViewHolder(val binding: ItemBookmarkPlantBinding) :
        RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemBookmarkPlantBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val plant = getItem(position)
        holder.binding.apply {
            tvPlantName.text = plant.name
            tvFlowerLanguage.text = "#${plant.flowerLanguage.split(",").firstOrNull()?.trim() ?: plant.flowerLanguage}"

            plant.imageUrl?.let { url ->
                ivPlantImage.load(url) {
                    crossfade(true)
                    placeholder(R.drawable.bg_image_placeholder)
                    error(R.drawable.bg_image_placeholder)
                }
            } ?: run {
                ivPlantImage.setImageResource(R.drawable.bg_image_placeholder)
            }

            root.setOnClickListener {
                onItemClick(plant)
            }
        }
    }

    private class DiffCallback : DiffUtil.ItemCallback<PlantCardDto>() {
        override fun areItemsTheSame(oldItem: PlantCardDto, newItem: PlantCardDto): Boolean {
            return oldItem.id == newItem.id
        }

        override fun areContentsTheSame(oldItem: PlantCardDto, newItem: PlantCardDto): Boolean {
            return oldItem == newItem
        }
    }
}
