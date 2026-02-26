package com.example.plant.data.model

import org.junit.Assert.*
import org.junit.Test

class FilterValidatorTest {

    // --- isValid ---

    @Test
    fun `SEASON SPRING 유효`() {
        assertTrue(FilterValidator.isValid(FilterType.SEASON, "SPRING"))
    }

    @Test
    fun `SEASON AUTUMN 무효 - FALL이 정답`() {
        assertFalse(FilterValidator.isValid(FilterType.SEASON, "AUTUMN"))
    }

    @Test
    fun `FLOWER_GROUP 사랑고백 유효`() {
        assertTrue(FilterValidator.isValid(FilterType.FLOWER_GROUP, "사랑/고백"))
    }

    @Test
    fun `FLOWER_GROUP 없는값 무효`() {
        assertFalse(FilterValidator.isValid(FilterType.FLOWER_GROUP, "없는값"))
    }

    @Test
    fun `STORY_GENRE 아무값이나 항상 유효`() {
        assertTrue(FilterValidator.isValid(FilterType.STORY_GENRE, "아무값"))
        assertTrue(FilterValidator.isValid(FilterType.STORY_GENRE, ""))
        assertTrue(FilterValidator.isValid(FilterType.STORY_GENRE, "판타지"))
    }

    @Test
    fun `COLOR_GROUP 유효한 값`() {
        assertTrue(FilterValidator.isValid(FilterType.COLOR_GROUP, "백색/미색"))
        assertTrue(FilterValidator.isValid(FilterType.COLOR_GROUP, "푸른색"))
    }

    @Test
    fun `SCENT_GROUP 유효한 값`() {
        assertTrue(FilterValidator.isValid(FilterType.SCENT_GROUP, "달콤·화사"))
        assertTrue(FilterValidator.isValid(FilterType.SCENT_GROUP, "무향"))
    }

    @Test
    fun `CATEGORY_GROUP 유효한 값`() {
        assertTrue(FilterValidator.isValid(FilterType.CATEGORY_GROUP, "꽃과 풀"))
        assertFalse(FilterValidator.isValid(FilterType.CATEGORY_GROUP, "없는분류"))
    }

    // --- getValidValues ---

    @Test
    fun `SEASON 유효값 4개`() {
        assertEquals(4, FilterValidator.getValidValues(FilterType.SEASON).size)
    }

    @Test
    fun `FLOWER_GROUP 유효값 5개`() {
        assertEquals(5, FilterValidator.getValidValues(FilterType.FLOWER_GROUP).size)
    }

    @Test
    fun `STORY_GENRE 유효값 비어있음`() {
        assertEquals(0, FilterValidator.getValidValues(FilterType.STORY_GENRE).size)
    }

    @Test
    fun `COLOR_GROUP 유효값 5개`() {
        assertEquals(5, FilterValidator.getValidValues(FilterType.COLOR_GROUP).size)
    }

    @Test
    fun `SCENT_GROUP 유효값 4개`() {
        assertEquals(4, FilterValidator.getValidValues(FilterType.SCENT_GROUP).size)
    }
}
