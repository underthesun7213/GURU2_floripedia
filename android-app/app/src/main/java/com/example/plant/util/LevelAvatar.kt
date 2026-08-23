package com.example.plant.util

import android.widget.ImageView
import androidx.annotation.DrawableRes
import com.example.plant.R

/**
 * 레벨(1~10) 칭호와 연동된 성장형 아바타.
 * 프로필 사진 대신 씨앗→새싹→…→숲으로 자라는 아이콘을 표시한다.
 * 아이콘: Material Symbols (Apache 2.0)
 */
object LevelAvatar {

    private data class Style(
        @DrawableRes val iconRes: Int,
        val bgColor: Int,
        val iconTint: Int
    )

    // index = level - 1. 배경/틴트는 성장에 따라 연녹→진녹, 7(꽃)은 핑크, 10(마스터)은 금색 포인트.
    private val STYLES = listOf(
        Style(R.drawable.ic_avatar_lv1_seed, 0xFFF1F2F6.toInt(), 0xFFA1887F.toInt()),      // 1 씨앗
        Style(R.drawable.ic_avatar_lv2_sprout, 0xFFE8F5E9.toInt(), 0xFF81C784.toInt()),    // 2 새싹
        Style(R.drawable.ic_avatar_lv3_leaf, 0xFFE8F5E9.toInt(), 0xFF66BB6A.toInt()),      // 3 떡잎
        Style(R.drawable.ic_avatar_lv4_grass, 0xFFDCEDC8.toInt(), 0xFF558B2F.toInt()),     // 4 어린잎
        Style(R.drawable.ic_avatar_lv5_stem, 0xFFC8E6C9.toInt(), 0xFF388E3C.toInt()),      // 5 줄기
        Style(R.drawable.ic_avatar_lv6_bud, 0xFFB2DFDB.toInt(), 0xFF00796B.toInt()),       // 6 꽃봉오리
        Style(R.drawable.ic_avatar_lv7_flower, 0xFFFCE4EC.toInt(), 0xFFEC407A.toInt()),    // 7 꽃송이
        Style(R.drawable.ic_avatar_lv8_explorer, 0xFFE0F2F1.toInt(), 0xFF00897B.toInt()),  // 8 식물 탐험가
        Style(R.drawable.ic_avatar_lv9_expert, 0xFFC8E6C9.toInt(), 0xFF2E7D32.toInt()),    // 9 식물 전문가
        Style(R.drawable.ic_avatar_lv10_master, 0xFFFFF8E1.toInt(), 0xFFF9A825.toInt())    // 10 식물 마스터
    )

    fun apply(imageView: ImageView, level: Int) {
        val style = STYLES[(level - 1).coerceIn(0, STYLES.lastIndex)]
        imageView.setBackgroundColor(style.bgColor)
        imageView.setImageResource(style.iconRes)
        imageView.setColorFilter(style.iconTint)
    }
}
