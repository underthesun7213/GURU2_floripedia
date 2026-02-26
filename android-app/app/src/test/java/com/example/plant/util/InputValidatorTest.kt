package com.example.plant.util

import org.junit.Assert.*
import org.junit.Test

class InputValidatorTest {

    // --- Password ---

    @Test
    fun `password 6자 이상이면 유효`() {
        assertTrue(InputValidator.isValidPassword("abc123"))
    }

    @Test
    fun `password 6자 미만이면 무효`() {
        assertFalse(InputValidator.isValidPassword("abc"))
    }

    @Test
    fun `password 빈 문자열이면 무효`() {
        assertFalse(InputValidator.isValidPassword(""))
    }

    // --- Nickname ---

    @Test
    fun `nickname 한글만 유효`() {
        assertTrue(InputValidator.isValidNickname("식물탐험가"))
    }

    @Test
    fun `nickname 영문 숫자 혼합 유효`() {
        assertTrue(InputValidator.isValidNickname("plant01"))
    }

    @Test
    fun `nickname 특수문자 포함시 무효`() {
        assertFalse(InputValidator.isValidNickname("nick@!"))
    }

    @Test
    fun `nickname 20자 초과시 무효`() {
        val longName = "가".repeat(21)
        assertFalse(InputValidator.isValidNickname(longName))
    }

    @Test
    fun `nickname 빈 문자열이면 무효`() {
        assertFalse(InputValidator.isValidNickname(""))
    }

    // --- Situation ---

    @Test
    fun `situation 10자 이상이면 유효`() {
        assertTrue(InputValidator.isValidSituation("가".repeat(10)))
    }

    @Test
    fun `situation 10자 미만이면 무효`() {
        assertFalse(InputValidator.isValidSituation("가".repeat(9)))
    }

    @Test
    fun `situation 500자 초과시 무효`() {
        assertFalse(InputValidator.isValidSituation("가".repeat(501)))
    }

    // --- Image Format ---

    @Test
    fun `image JPEG 매직바이트 유효`() {
        val jpeg = byteArrayOf(0xFF.toByte(), 0xD8.toByte(), 0xFF.toByte(), 0xE0.toByte())
        assertTrue(InputValidator.isValidImageFormat(jpeg))
    }

    @Test
    fun `image PNG 매직바이트 유효`() {
        val png = byteArrayOf(0x89.toByte(), 0x50.toByte(), 0x4E.toByte(), 0x47.toByte())
        assertTrue(InputValidator.isValidImageFormat(png))
    }

    @Test
    fun `image 랜덤 바이트 무효`() {
        val random = byteArrayOf(0x00, 0x01, 0x02, 0x03)
        assertFalse(InputValidator.isValidImageFormat(random))
    }

    @Test
    fun `image 3바이트 미만 무효`() {
        val small = byteArrayOf(0xFF.toByte(), 0xD8.toByte())
        assertFalse(InputValidator.isValidImageFormat(small))
    }

    // --- Image Size ---

    @Test
    fun `imageSize 10MB 이하면 유효`() {
        val data = ByteArray(10 * 1024 * 1024) // exactly 10MB
        assertTrue(InputValidator.isValidImageSize(data))
    }

    @Test
    fun `imageSize 10MB 초과시 무효`() {
        val data = ByteArray(10 * 1024 * 1024 + 1)
        assertFalse(InputValidator.isValidImageSize(data))
    }

    // --- Search Keyword ---

    @Test
    fun `searchKeyword 빈 문자열 무효`() {
        assertFalse(InputValidator.isValidSearchKeyword(""))
    }

    @Test
    fun `searchKeyword 100자 이하 유효`() {
        assertTrue(InputValidator.isValidSearchKeyword("장미"))
    }

    @Test
    fun `searchKeyword 100자 초과 무효`() {
        assertFalse(InputValidator.isValidSearchKeyword("가".repeat(101)))
    }
}
