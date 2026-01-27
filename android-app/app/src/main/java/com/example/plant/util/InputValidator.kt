package com.example.plant.util

import android.util.Patterns
import java.util.regex.Pattern

/**
 * 입력값 Validation 유틸리티
 */
object InputValidator {
    
    /**
     * 이메일 형식 검증
     */
    fun isValidEmail(email: String): Boolean {
        return email.isNotEmpty() && Patterns.EMAIL_ADDRESS.matcher(email).matches()
    }
    
    /**
     * 비밀번호 검증 (최소 6자)
     */
    fun isValidPassword(password: String): Boolean {
        return password.length >= 6
    }
    
    /**
     * 닉네임 검증 (1-20자, 특수문자 제한)
     */
    fun isValidNickname(nickname: String): Boolean {
        if (nickname.isEmpty() || nickname.length > 20) {
            return false
        }
        // 한글, 영문, 숫자, 공백만 허용
        val pattern = Pattern.compile("^[가-힣a-zA-Z0-9\\s]+$")
        return pattern.matcher(nickname).matches()
    }
    
    /**
     * 검색어 검증 (1-100자)
     */
    fun isValidSearchKeyword(keyword: String): Boolean {
        return keyword.isNotEmpty() && keyword.length <= 100
    }
    
    /**
     * 상황 입력 검증 (10-500자)
     */
    fun isValidSituation(situation: String): Boolean {
        return situation.length >= 10 && situation.length <= 500
    }
    
    /**
     * 이미지 파일 크기 검증 (최대 10MB)
     */
    fun isValidImageSize(imageData: ByteArray): Boolean {
        val maxSizeInBytes = 10 * 1024 * 1024 // 10MB
        return imageData.size <= maxSizeInBytes
    }
    
    /**
     * 이미지 파일 형식 검증 (JPEG, PNG)
     */
    fun isValidImageFormat(imageData: ByteArray): Boolean {
        if (imageData.size < 4) return false
        
        // JPEG: FF D8 FF
        val isJpeg = imageData[0] == 0xFF.toByte() && 
                     imageData[1] == 0xD8.toByte() && 
                     imageData[2] == 0xFF.toByte()
        
        // PNG: 89 50 4E 47
        val isPng = imageData[0] == 0x89.toByte() && 
                    imageData[1] == 0x50.toByte() && 
                    imageData[2] == 0x4E.toByte() && 
                    imageData[3] == 0x47.toByte()
        
        return isJpeg || isPng
    }
    
    /**
     * 빈 문자열 검증
     */
    fun isNotEmpty(value: String): Boolean {
        return value.trim().isNotEmpty()
    }
}
