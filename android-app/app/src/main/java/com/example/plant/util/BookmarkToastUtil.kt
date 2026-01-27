package com.example.plant.util

import android.app.Activity
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.widget.FrameLayout
import android.widget.ImageView
import com.example.plant.R

/**
 * 커스텀 북마크 토스트 유틸리티
 */
object BookmarkToastUtil {

    /**
     * 북마크 저장 완료 커스텀 토스트 표시
     */
    fun showBookmarkSavedToast(activity: Activity) {
        val rootView = activity.findViewById<FrameLayout>(android.R.id.content)
        val inflater = LayoutInflater.from(activity)
        val toastView = inflater.inflate(R.layout.toast_bookmark, rootView, false)

        // 중앙 정렬
        val params = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.WRAP_CONTENT,
            FrameLayout.LayoutParams.WRAP_CONTENT
        ).apply {
            gravity = Gravity.CENTER
        }

        rootView.addView(toastView, params)

        // 페이드 인
        toastView.alpha = 0f
        toastView.animate()
            .alpha(1f)
            .setDuration(200)
            .start()

        // 2초 후 페이드 아웃 및 제거
        Handler(Looper.getMainLooper()).postDelayed({
            toastView.animate()
                .alpha(0f)
                .setDuration(200)
                .withEndAction {
                    rootView.removeView(toastView)
                }
                .start()
        }, 1500)
    }
}
