package com.example.plant.ui.home

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import coil.load
import com.example.plant.R
import com.example.plant.databinding.ItemStoryBinding
import com.example.plant.data.model.Plant

class StoryAdapter(
    private val onPlantClick: (Plant) -> Unit
) : ListAdapter<Plant, StoryAdapter.StoryViewHolder>(PlantDiffCallback()) {

    inner class StoryViewHolder(val binding: ItemStoryBinding) :
        androidx.recyclerview.widget.RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): StoryViewHolder {
        val binding = ItemStoryBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return StoryViewHolder(binding)
    }

    override fun onBindViewHolder(holder: StoryViewHolder, position: Int) {
        val plant = getItem(position)
        holder.binding.apply {
            tvStoryTitle.text = plant.name
            tvStoryDescription.text = plant.story

            ivStory.load(plant.imageUrl) {
                crossfade(true)
                placeholder(R.drawable.rose)
            }

            // 카드 전체 클릭 리스너
            root.setOnClickListener {
                onPlantClick(plant)
            }
        }
    }

    private class PlantDiffCallback : DiffUtil.ItemCallback<Plant>() {
        override fun areItemsTheSame(oldItem: Plant, newItem: Plant): Boolean {
            return oldItem.plantId == newItem.plantId
        }

        override fun areContentsTheSame(oldItem: Plant, newItem: Plant): Boolean {
            return oldItem == newItem
        }
    }
}
