package com.example.plant.data.api

import com.example.plant.data.remote.api.PlantApi
import com.example.plant.data.remote.dto.response.*
import com.google.gson.Gson
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class ApiParsingTest {

    private lateinit var server: MockWebServer
    private lateinit var api: PlantApi

    @Before
    fun setup() {
        server = MockWebServer()
        server.start()
        api = Retrofit.Builder()
            .baseUrl(server.url("/"))
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(PlantApi::class.java)
    }

    @After
    fun teardown() {
        server.shutdown()
    }

    @Test
    fun `식물 목록 JSON 파싱`() = runTest {
        val json = """
        [
            {
                "_id": "1",
                "name": "장미",
                "flowerLanguage": "사랑",
                "imageUrl": "https://example.com/rose.jpg",
                "season": "SPRING",
                "preContent": "장미는 아름다운 꽃입니다"
            },
            {
                "_id": "2",
                "name": "해바라기",
                "flowerLanguage": "동경",
                "imageUrl": null,
                "season": "SUMMER",
                "preContent": null
            }
        ]
        """.trimIndent()

        server.enqueue(MockResponse().setBody(json).setResponseCode(200))
        val response = api.getPlants()

        assertTrue(response.isSuccessful)
        val plants = response.body()!!
        assertEquals(2, plants.size)
        assertEquals("장미", plants[0].name)
        assertEquals("1", plants[0].id)
        assertEquals("사랑", plants[0].flowerLanguage)
        assertEquals("SPRING", plants[0].season)
        assertNull(plants[1].imageUrl)
    }

    @Test
    fun `식물 상세 중첩 DTO 파싱`() = runTest {
        val json = """
        {
            "_id": "1",
            "name": "장미",
            "scientificName": "Rosa",
            "isRepresentative": true,
            "taxonomy": {
                "genus": "Rosa",
                "species": "Rosa hybrida",
                "family": "장미과"
            },
            "horticulture": {
                "category": "관상용",
                "categoryGroup": "꽃과 풀",
                "usage": ["절화", "정원"],
                "management": "가지치기 필요",
                "preContent": "관리가 쉬운 꽃"
            },
            "habitat": "온대 지역",
            "flowerInfo": {
                "language": "사랑",
                "flowerGroup": "사랑/고백"
            },
            "stories": [
                {"genre": "신화", "content": "그리스 신화의 장미"}
            ],
            "images": ["img1.jpg", "img2.jpg"],
            "imageUrl": "https://example.com/rose.jpg",
            "season": "SPRING",
            "bloomingMonths": [4, 5, 6],
            "searchKeywords": ["장미", "로즈"],
            "popularityScore": 95,
            "colorInfo": {
                "hexCodes": ["#FF0000"],
                "colorLabels": ["빨강"],
                "colorGroup": ["빨강/분홍"]
            },
            "scentInfo": {
                "scentTags": ["달콤한"],
                "scentGroup": ["달콤·화사"]
            },
            "isFavorite": false
        }
        """.trimIndent()

        server.enqueue(MockResponse().setBody(json).setResponseCode(200))
        val response = api.getPlantDetail("1")

        assertTrue(response.isSuccessful)
        val detail = response.body()!!
        assertEquals("장미", detail.name)
        assertEquals("Rosa", detail.scientificName)
        assertTrue(detail.isRepresentative)
        // taxonomy
        assertEquals("장미과", detail.taxonomy.family)
        // horticulture
        assertEquals("꽃과 풀", detail.horticulture.categoryGroup)
        assertEquals(2, detail.horticulture.usage.size)
        // flowerInfo
        assertEquals("사랑", detail.flowerInfo.language)
        assertEquals("사랑/고백", detail.flowerInfo.flowerGroup)
        // stories
        assertEquals(1, detail.stories.size)
        assertEquals("신화", detail.stories[0].genre)
        // collections
        assertEquals(listOf(4, 5, 6), detail.bloomingMonths)
        assertEquals(95, detail.popularityScore)
        // colorInfo
        assertEquals("#FF0000", detail.colorInfo.hexCodes[0])
        // scentInfo
        assertEquals("달콤·화사", detail.scentInfo.scentGroup[0])
        assertFalse(detail.isFavorite)
    }

    @Test
    fun `UserResponse 파싱`() = runTest {
        val json = """
        {
            "_id": "user1",
            "email": "test@example.com",
            "nickname": "식물러버",
            "profileImageUrl": "https://example.com/profile.jpg",
            "favoritePlantIds": ["p1", "p2", "p3"],
            "createdAt": "2024-01-01T00:00:00Z"
        }
        """.trimIndent()

        val user = Gson().fromJson(json, UserResponse::class.java)

        assertEquals("user1", user.id)
        assertEquals("test@example.com", user.email)
        assertEquals("식물러버", user.nickname)
        assertEquals(3, user.favoritePlantIds.size)
        assertNotNull(user.profileImageUrl)
    }

    @Test
    fun `FavoriteToggleResponse 파싱`() = runTest {
        val json = """{"isFavorite": true, "message": "즐겨찾기에 추가되었습니다"}"""

        val result = Gson().fromJson(json, FavoriteToggleResponse::class.java)

        assertTrue(result.isFavorite)
        assertEquals("즐겨찾기에 추가되었습니다", result.message)
    }

    @Test
    fun `404 에러 응답 처리`() = runTest {
        server.enqueue(MockResponse().setResponseCode(404).setBody("""{"detail":"Not found"}"""))
        val response = api.getPlantDetail("nonexistent")

        assertFalse(response.isSuccessful)
        assertEquals(404, response.code())
    }
}
