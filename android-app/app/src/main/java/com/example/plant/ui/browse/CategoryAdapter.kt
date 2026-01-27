package com.example.plant.ui.browse

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.RecyclerView
import com.example.plant.R
import com.example.plant.data.model.FilterCategory
import com.google.android.material.imageview.ShapeableImageView

class CategoryAdapter(
    private var categories: List<FilterCategory>,
    private val onCategoryClick: (FilterCategory) -> Unit
) : RecyclerView.Adapter<CategoryAdapter.ViewHolder>() {

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val ivCategory: ShapeableImageView = view.findViewById(R.id.ivCategory)
        val tvCategory: TextView = view.findViewById(R.id.tvCategoryName)
        val root: View = view
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_category, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = categories[position]
        holder.tvCategory.text = item.name
        holder.ivCategory.setImageResource(item.imageRes)
        
        val context = holder.itemView.context
        
        if (item.isSelected) {
            // 하드코딩된 리소스 대신 직접 픽셀값 계산 (4dp)
            val strokePx = (4 * context.resources.displayMetrics.density).toInt()
            holder.ivCategory.strokeWidth = strokePx.toFloat()
            holder.ivCategory.strokeColor = ContextCompat.getColorStateList(context, R.color.button)
            holder.tvCategory.setTextColor(ContextCompat.getColor(context, R.color.text1))
            holder.tvCategory.paint.isFakeBoldText = true
        } else {
            holder.ivCategory.strokeWidth = 0f
            holder.tvCategory.setTextColor(ContextCompat.getColor(context, R.color.sub_text1))
            holder.tvCategory.paint.isFakeBoldText = false
        }
        
        holder.root.setOnClickListener {
            onCategoryClick(item)
        }
    }

    override fun getItemCount() = categories.size

    fun updateData(newCategories: List<FilterCategory>) {
        this.categories = newCategories
        notifyDataSetChanged()
    }
}
