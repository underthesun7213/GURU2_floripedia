package com.example.plant

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import coil.load // 이미지 로딩 라이브러리 사용 시
import com.example.plant.databinding.ItemStoryBinding

class StoryAdapter(private val plantList: List<Plant>) :
    RecyclerView.Adapter<StoryAdapter.StoryViewHolder>() {

    inner class StoryViewHolder(val binding: ItemStoryBinding) :
        RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): StoryViewHolder {
        val binding = ItemStoryBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return StoryViewHolder(binding)
    }

    override fun onBindViewHolder(holder: StoryViewHolder, position: Int) {
        val plant = plantList[position]
        holder.binding.apply {
            // Plant 모델의 데이터를 뷰에 매핑
            tvStoryTitle.text = plant.name
            tvStoryDescription.text = plant.story

            // 이미지 URL 로드 (Coil 예시)
            ivStory.load(plant.imageUrl) {
                crossfade(true)
                placeholder(R.drawable.rose) // 로딩 중 임시 이미지
            }
        }
    }

    override fun getItemCount(): Int = plantList.size
}