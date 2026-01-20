package com.example.plant

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import coil.load
import com.example.plant.databinding.ItemFeaturedPlantBinding

// 매개변수 타입을 List<Plant>로 설정합니다.
class FeaturedPlantAdapter(private val plantList: List<Plant>) :
    RecyclerView.Adapter<FeaturedPlantAdapter.PlantViewHolder>() {

    inner class PlantViewHolder(val binding: ItemFeaturedPlantBinding) :
        RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): PlantViewHolder {
        val binding = ItemFeaturedPlantBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return PlantViewHolder(binding)
    }

    override fun onBindViewHolder(holder: PlantViewHolder, position: Int) {
        val plant = plantList[position]
        holder.binding.apply {
            tvPlantName.text = plant.name //
            tvDescription.text = plant.story //

            // Coil 라이브러리로 이미지 로드
            ivPlant.load(plant.imageUrl) {
                crossfade(true)
                placeholder(android.R.color.darker_gray)
            }
        }
    }

    override fun getItemCount(): Int = plantList.size
}