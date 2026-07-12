package com.example.plant.ui.mypage

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import coil.load
import com.example.plant.R
import com.example.plant.databinding.ItemMypageRecentPlantBinding
import com.example.plant.util.loadPlantImage
import com.example.plant.util.RecentPlantManager.RecentPlant

class MyPageRecentPlantAdapter(
    private val onItemClick: (RecentPlant) -> Unit
) : ListAdapter<RecentPlant, MyPageRecentPlantAdapter.ViewHolder>(DiffCallback()) {

    inner class ViewHolder(val binding: ItemMypageRecentPlantBinding) :
        RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemMypageRecentPlantBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val plant = getItem(position)
        holder.binding.apply {
            tvPlantName.text = plant.name

            ivPlantImage.loadPlantImage(plant.imageUrl)

            root.setOnClickListener {
                onItemClick(plant)
            }
        }
    }

    private class DiffCallback : DiffUtil.ItemCallback<RecentPlant>() {
        override fun areItemsTheSame(oldItem: RecentPlant, newItem: RecentPlant): Boolean {
            return oldItem.id == newItem.id
        }

        override fun areContentsTheSame(oldItem: RecentPlant, newItem: RecentPlant): Boolean {
            return oldItem == newItem
        }
    }
}
