package com.example.plant

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import coil.load
import com.example.plant.databinding.ItemAvailablePlantBinding // 파일명이 이렇다면 유지

class AvailablePlantAdapter(private val plants: List<Plant>) :
    RecyclerView.Adapter<AvailablePlantAdapter.ViewHolder>() {

    inner class ViewHolder(val binding: ItemAvailablePlantBinding) :
        RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemAvailablePlantBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val plant = plants[position]
        holder.binding.apply {
            tvPlantGridName.text = plant.name
            ivPlantGrid.load(plant.imageUrl)
        }
    }

    override fun getItemCount() = plants.size
}