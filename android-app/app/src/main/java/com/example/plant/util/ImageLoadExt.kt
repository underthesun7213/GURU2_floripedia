package com.example.plant.util

import android.view.animation.Animation
import android.view.animation.LinearInterpolator
import android.view.animation.RotateAnimation
import android.widget.ImageView
import coil.load
import com.example.plant.R

/**
 * 식물 이미지 로딩 공통 헬퍼.
 * - URL이 없는(확정적으로 이미지가 없는) 식물: 회전 없이 정적 "준비 중" 플레이스홀더 표시.
 * - 실제 URL 로딩 중: 스피너 링을 표시하고 ImageView를 회전시킨다.
 * - 로딩 성공: 회전을 멈추고 실제 이미지 표시.
 * - 로딩 실패(네트워크 등): 무한 회전하지 않고 "준비 중" 플레이스홀더로 안착.
 *
 * <animated-rotate> 드로어블은 Coil placeholder로는 자동 회전하지 않으므로
 * 뷰 애니메이션(RotateAnimation)으로 확실하게 회전시킨다.
 */
fun ImageView.loadPlantImage(url: String?) {
    val iv = this
    // 이미지가 아예 없는 식물 → 회전 없이 정적 준비중 플레이스홀더
    if (url.isNullOrBlank()) {
        iv.stopSpin()
        iv.setImageResource(R.drawable.bg_image_pending)
        return
    }
    load(url) {
        crossfade(true)
        placeholder(R.drawable.bg_image_placeholder)
        error(R.drawable.bg_image_pending)
        listener(
            onStart = { iv.startSpin() },
            onSuccess = { _, _ -> iv.stopSpin() },
            onError = { _, _ -> iv.stopSpin() },   // 실패해도 무한 회전하지 않고 준비중으로 안착
            onCancel = { iv.stopSpin() }
        )
    }
}

private fun ImageView.startSpin() {
    if (animation != null && !animation.hasEnded()) return
    val spin = RotateAnimation(
        0f, 360f,
        Animation.RELATIVE_TO_SELF, 0.5f,
        Animation.RELATIVE_TO_SELF, 0.5f
    ).apply {
        duration = 1000L
        repeatCount = Animation.INFINITE
        interpolator = LinearInterpolator()
    }
    startAnimation(spin)
}

private fun ImageView.stopSpin() {
    clearAnimation()
}
