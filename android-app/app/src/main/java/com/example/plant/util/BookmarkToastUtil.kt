package com.example.plant.util

import android.app.Activity
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.LayoutInflater
import android.widget.FrameLayout
import com.example.plant.R

/**
 * 커스텀 북마크 토스트 유틸리티
 */
object BookmarkToastUtil {

    /**
     * 북마크 저장 완료 커스텀 토스트 표시 (하단에서 슬라이드 업)
     */
    fun showBookmarkSavedToast(activity: Activity) {
        val rootView = activity.findViewById<FrameLayout>(android.R.id.content)
        val inflater = LayoutInflater.from(activity)
        val toastView = inflater.inflate(R.layout.toast_bookmark, rootView, false)

        // 하단 중앙 정렬, 바텀 네비게이션 위에 표시
        val params = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.WRAP_CONTENT,
            FrameLayout.LayoutParams.WRAP_CONTENT
        ).apply {
            gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
            bottomMargin = 120.dpToPx(activity)
        }

        rootView.addView(toastView, params)

        // 초기 상태: 아래에서 시작, 투명
        toastView.translationY = 50f
        toastView.alpha = 0f

        // 슬라이드 업 + 페이드 인 애니메이션
        toastView.animate()
            .translationY(0f)
            .alpha(1f)
            .setDuration(250)
            .start()

        // 1.5초 후 슬라이드 다운 + 페이드 아웃
        Handler(Looper.getMainLooper()).postDelayed({
            toastView.animate()
                .translationY(50f)
                .alpha(0f)
                .setDuration(250)
                .withEndAction {
                    rootView.removeView(toastView)
                }
                .start()
        }, 1500)
    }

    private fun Int.dpToPx(activity: Activity): Int {
        return (this * activity.resources.displayMetrics.density).toInt()
    }
}
