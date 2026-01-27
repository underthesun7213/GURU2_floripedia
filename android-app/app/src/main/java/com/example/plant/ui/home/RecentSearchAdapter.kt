package com.example.plant.ui.home

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.plant.R
import com.example.plant.util.RecentPlantManager

/**
 * 최근 검색어 RecyclerView Adapter
 */
class RecentSearchAdapter(
    private val onItemClick: (RecentPlantManager.RecentPlant) -> Unit
) : ListAdapter<RecentPlantManager.RecentPlant, RecentSearchAdapter.ViewHolder>(DiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_recent_search, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvPlantName: TextView = itemView.findViewById(R.id.tvRecentSearch) ?: itemView as TextView

        fun bind(plant: RecentPlantManager.RecentPlant) {
            tvPlantName.text = plant.name
            itemView.setOnClickListener {
                onItemClick(plant)
            }
        }
    }

    private class DiffCallback : DiffUtil.ItemCallback<RecentPlantManager.RecentPlant>() {
        override fun areItemsTheSame(
            oldItem: RecentPlantManager.RecentPlant,
            newItem: RecentPlantManager.RecentPlant
        ): Boolean = oldItem.id == newItem.id

        override fun areContentsTheSame(
            oldItem: RecentPlantManager.RecentPlant,
            newItem: RecentPlantManager.RecentPlant
        ): Boolean = oldItem == newItem
    }
}
