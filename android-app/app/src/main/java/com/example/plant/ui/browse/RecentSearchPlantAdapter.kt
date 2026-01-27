package com.example.plant.ui.browse

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import coil.load
import com.example.plant.R
import com.example.plant.databinding.ItemSearchFlowerBinding
import com.example.plant.util.RecentPlantManager.RecentPlant

class RecentSearchPlantAdapter(
    private val onItemClick: (RecentPlant) -> Unit
) : ListAdapter<RecentPlant, RecentSearchPlantAdapter.ViewHolder>(DiffCallback()) {

    inner class ViewHolder(val binding: ItemSearchFlowerBinding) :
        RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemSearchFlowerBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val plant = getItem(position)
        holder.binding.apply {
            tvSearchFlowerName.text = plant.name
            tvSearchFlowerDesc.text = plant.description ?: "${plant.name}은 구근 식물로 봄에 개화하며"

            plant.imageUrl?.let { url ->
                ivSearchFlower.load(url) {
                    crossfade(true)
                    placeholder(R.drawable.bg_image_placeholder)
                    error(R.drawable.bg_image_placeholder)
                }
            } ?: run {
                ivSearchFlower.setImageResource(R.drawable.bg_image_placeholder)
            }

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
