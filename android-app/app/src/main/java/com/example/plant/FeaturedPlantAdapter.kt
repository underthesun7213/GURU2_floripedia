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
            tvPlantName.text = plant.name
            tvDescription.text = plant.story

            // 1. 태그 데이터 추가 (Plant 모델의 속성 활용)
            tvTag1.text = "#${plant.flowerLanguage}" // 예: #첫사랑
            tvTag2.text = if (plant.scentTags.isNotEmpty()) "#${plant.scentTags[0]}" else "#${plant.season}"

            // 2. Coil 라이브러리로 이미지 로드
            ivPlant.load(plant.imageUrl) {
                crossfade(true)
                placeholder(android.R.color.darker_gray)
                // 이미지 모서리를 레이아웃 스타일에 맞춰 둥글게 처리하고 싶다면 아래 줄 추가
                // transformations(RoundedCornersTransformation(40f))
            }
        }
    }

    override fun getItemCount(): Int = plantList.size
}