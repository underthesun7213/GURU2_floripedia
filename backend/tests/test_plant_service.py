"""
PlantService 통합 테스트
- 이미지 기반 검색 (search_by_image)
- 텍스트 기반 추천 (recommend_plants)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.plant_service import PlantService
from app.repositories.plant_repository import PlantRepository


class TestSearchByImage:
    """이미지 기반 식물 검색 테스트"""

    @pytest.mark.asyncio
    async def test_search_found_by_scientific_name(self, plant_repo, mock_gemini_service):
        """학명 정확 일치로 검색 성공"""
        # Arrange
        user_repo = MagicMock()
        user_repo.get_favorites = AsyncMock(return_value=[])
        service = PlantService(plant_repo, user_repo, mock_gemini_service)

        mock_gemini_service.get_plant_name_from_image = AsyncMock(return_value={
            "name": "장미",
            "englishName": "Rose",
            "scientificName": "Rosa canina"
        })

        # Act
        result = await service.search_by_image(b"fake_image_data", user_id=None)

        # Assert
        assert result is not None
        assert result["name"] == "장미"
        assert result["is_newly_created"] == False

    @pytest.mark.asyncio
    async def test_search_found_by_fuzzy_match(self, plant_repo, mock_gemini_service):
        """학명 퍼지 매칭으로 검색 성공 (속 일치)"""
        # Arrange
        user_repo = MagicMock()
        user_repo.get_favorites = AsyncMock(return_value=[])
        service = PlantService(plant_repo, user_repo, mock_gemini_service)

        # Gemini가 "Rosa rugosa"를 반환했지만, DB에는 "Rosa canina"만 있음
        mock_gemini_service.get_plant_name_from_image = AsyncMock(return_value={
            "name": "찔레장미",
            "englishName": "Rugosa Rose",
            "scientificName": "Rosa rugosa"
        })

        # Act
        result = await service.search_by_image(b"fake_image_data", user_id=None)

        # Assert
        assert result is not None
        assert result["scientificName"].startswith("Rosa")  # 같은 속(genus)

    @pytest.mark.asyncio
    async def test_search_not_found_raises_error(self, plant_repo, mock_gemini_service):
        """DB에 없는 식물 검색 시 ValueError 발생"""
        # Arrange
        user_repo = MagicMock()
        service = PlantService(plant_repo, user_repo, mock_gemini_service)

        mock_gemini_service.get_plant_name_from_image = AsyncMock(return_value={
            "name": "희귀난초",
            "englishName": "Rare Orchid",
            "scientificName": "Orchis rara"
        })

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await service.search_by_image(b"fake_image_data", user_id=None)

        assert "데이터베이스에 없습니다" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_not_found_logs_miss(self, plant_repo, mock_gemini_service):
        """DB 미스 시 search_misses에 기록되고, 반복 시 count가 증가한다"""
        # Arrange
        user_repo = MagicMock()
        service = PlantService(plant_repo, user_repo, mock_gemini_service)

        mock_gemini_service.get_plant_name_from_image = AsyncMock(return_value={
            "name": "블루세이지",
            "englishName": "Blue Sage",
            "scientificName": "Salvia azurea"
        })

        # Act: 1회 미스 후 firstSeenAt 기록
        with pytest.raises(ValueError):
            await service.search_by_image(b"fake_image_data", user_id=None)
        first = await plant_repo.search_misses.find_one({"_id": "salvia azurea"})

        # Act: 같은 미스 1회 더
        with pytest.raises(ValueError):
            await service.search_by_image(b"fake_image_data", user_id=None)

        # Assert: 학명 소문자 키로 upsert, count 누적
        doc = await plant_repo.search_misses.find_one({"_id": "salvia azurea"})
        assert doc is not None
        assert doc["count"] == 2
        assert doc["name"] == "블루세이지"
        assert doc["scientificName"] == "Salvia azurea"
        assert doc["englishName"] == "Blue Sage"
        # $setOnInsert 회귀 방지: firstSeenAt은 1회차 값 그대로, lastSeenAt만 갱신
        assert doc["firstSeenAt"] == first["firstSeenAt"]
        assert doc["lastSeenAt"] >= doc["firstSeenAt"]

    @pytest.mark.asyncio
    async def test_miss_key_falls_back_to_name(self, plant_repo, mock_gemini_service):
        """학명이 빈 값이면 이름 소문자가 미스 키가 된다"""
        # Arrange
        user_repo = MagicMock()
        service = PlantService(plant_repo, user_repo, mock_gemini_service)

        mock_gemini_service.get_plant_name_from_image = AsyncMock(return_value={
            "name": "희귀난초",
            "englishName": "Rare Orchid",
            "scientificName": ""
        })

        # Act
        with pytest.raises(ValueError):
            await service.search_by_image(b"fake_image_data", user_id=None)

        # Assert
        doc = await plant_repo.search_misses.find_one({"_id": "희귀난초"})
        assert doc is not None
        assert doc["count"] == 1

    @pytest.mark.asyncio
    async def test_miss_log_failure_does_not_change_response(self, plant_repo, mock_gemini_service):
        """미스 기록이 실패해도 원래 에러 응답은 그대로 유지된다"""
        # Arrange
        user_repo = MagicMock()
        service = PlantService(plant_repo, user_repo, mock_gemini_service)
        plant_repo.log_search_miss = AsyncMock(side_effect=RuntimeError("db down"))

        mock_gemini_service.get_plant_name_from_image = AsyncMock(return_value={
            "name": "희귀난초",
            "englishName": "Rare Orchid",
            "scientificName": "Orchis rara"
        })

        # Act & Assert: RuntimeError가 아니라 기존 ValueError가 나와야 함
        with pytest.raises(ValueError) as exc_info:
            await service.search_by_image(b"fake_image_data", user_id=None)

        assert "데이터베이스에 없습니다" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_not_plant_image(self, plant_repo, mock_gemini_service):
        """식물이 아닌 이미지 업로드 시 ValueError 발생"""
        # Arrange
        user_repo = MagicMock()
        service = PlantService(plant_repo, user_repo, mock_gemini_service)

        mock_gemini_service.get_plant_name_from_image = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await service.search_by_image(b"cat_image_data", user_id=None)

        assert "식별할 수 없습니다" in str(exc_info.value)


class TestRecommendPlants:
    """텍스트 기반 식물 추천 테스트"""

    @pytest.mark.asyncio
    async def test_recommend_found_with_essay(self, plant_repo, mock_gemini_service):
        """추천 성공 + 에세이 생성"""
        # Arrange
        user_repo = MagicMock()
        service = PlantService(plant_repo, user_repo, mock_gemini_service)

        mock_gemini_service.get_plant_name_from_text = AsyncMock(return_value={
            "name": "라벤더",
            "englishName": "Lavender",
            "scientificName": "Lavandula angustifolia"
        })
        mock_gemini_service.generate_recommendation_essay = AsyncMock(
            return_value="라벤더의 은은한 향기가 마음을 편안하게 해줄 거예요."
        )

        # Act
        result = await service.recommend_plants("우울할 때 위로가 되는 꽃")

        # Assert
        assert result is not None
        assert result["name"] == "라벤더"
        assert "recommendation" in result
        assert "라벤더" in result["recommendation"]

    @pytest.mark.asyncio
    async def test_recommend_not_found_raises_error(self, plant_repo, mock_gemini_service):
        """DB에 없는 식물 추천 시 ValueError 발생"""
        # Arrange
        user_repo = MagicMock()
        service = PlantService(plant_repo, user_repo, mock_gemini_service)

        mock_gemini_service.get_plant_name_from_text = AsyncMock(return_value={
            "name": "에델바이스",
            "englishName": "Edelweiss",
            "scientificName": "Leontopodium alpinum"
        })

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await service.recommend_plants("알프스 고산지대 식물")

        assert "데이터베이스에 없습니다" in str(exc_info.value)

        # 추천 미스도 search_misses에 기록된다
        doc = await plant_repo.search_misses.find_one({"_id": "leontopodium alpinum"})
        assert doc is not None
        assert doc["count"] == 1

    @pytest.mark.asyncio
    async def test_recommend_miss_log_failure_does_not_change_response(self, plant_repo, mock_gemini_service):
        """추천 경로에서도 미스 기록 실패가 응답을 바꾸지 않는다"""
        # Arrange
        user_repo = MagicMock()
        service = PlantService(plant_repo, user_repo, mock_gemini_service)
        plant_repo.log_search_miss = AsyncMock(side_effect=RuntimeError("db down"))

        mock_gemini_service.get_plant_name_from_text = AsyncMock(return_value={
            "name": "에델바이스",
            "englishName": "Edelweiss",
            "scientificName": "Leontopodium alpinum"
        })

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await service.recommend_plants("알프스 고산지대 식물")

        assert "데이터베이스에 없습니다" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_recommend_gemini_fails(self, plant_repo, mock_gemini_service):
        """Gemini 추천 실패 시 ValueError 발생"""
        # Arrange
        user_repo = MagicMock()
        service = PlantService(plant_repo, user_repo, mock_gemini_service)

        mock_gemini_service.get_plant_name_from_text = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await service.recommend_plants("의미없는 입력")

        assert "추천하지 못했습니다" in str(exc_info.value)
