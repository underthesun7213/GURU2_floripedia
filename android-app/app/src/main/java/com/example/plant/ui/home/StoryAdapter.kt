package com.example.plant.ui.home

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import coil.load
import com.example.plant.R
import com.example.plant.databinding.ItemStoryBinding
import com.example.plant.util.loadPlantImage
import com.example.plant.data.remote.dto.response.PopularStoryDto

class StoryAdapter(
    private val onStoryClick: (PopularStoryDto) -> Unit
) : ListAdapter<PopularStoryDto, StoryAdapter.StoryViewHolder>(StoryDiffCallback()) {

    inner class StoryViewHolder(val binding: ItemStoryBinding) :
        androidx.recyclerview.widget.RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): StoryViewHolder {
        val binding = ItemStoryBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return StoryViewHolder(binding)
    }

    override fun onBindViewHolder(holder: StoryViewHolder, position: Int) {
        val story = getItem(position)
        holder.binding.apply {
            // 첫 문장을 제목으로 사용
            tvStoryTitle.text = extractTitle(story.content)
            tvStoryDescription.text = story.content

            ivStory.loadPlantImage(story.imageUrl)

            root.setOnClickListener {
                onStoryClick(story)
            }
        }
    }

    private fun extractTitle(content: String): String {
        // 첫 번째 문장(마침표/물음표/느낌표까지)을 제목으로 추출
        val endIndex = content.indexOfFirst { it == '.' || it == '?' || it == '!' }
        return if (endIndex in 0..30) {
            content.substring(0, endIndex + 1)
        } else {
            content.take(25) + "..."
        }
    }

    private class StoryDiffCallback : DiffUtil.ItemCallback<PopularStoryDto>() {
        override fun areItemsTheSame(oldItem: PopularStoryDto, newItem: PopularStoryDto): Boolean {
            return oldItem.plantId == newItem.plantId && oldItem.genre == newItem.genre
        }

        override fun areContentsTheSame(oldItem: PopularStoryDto, newItem: PopularStoryDto): Boolean {
            return oldItem == newItem
        }
    }
}
