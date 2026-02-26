"""
PlantRepository 단위 테스트
- find_by_scientific_name_fuzzy 메서드 검증
"""
import pytest

from app.repositories.plant_repository import PlantRepository


class TestFindByScientificNameFuzzy:
    """학명 퍼지 매칭 테스트"""

    @pytest.mark.asyncio
    async def test_exact_match(self, plant_repo: PlantRepository):
        """정확한 학명 일치 시 반환"""
        result = await plant_repo.find_by_scientific_name_fuzzy("Rosa canina")

        assert result is not None
        assert result["name"] == "장미"
        assert result["scientificName"] == "Rosa canina"

    @pytest.mark.asyncio
    async def test_genus_only_match(self, plant_repo: PlantRepository):
        """속(genus)만 일치해도 매칭"""
        # "Rosa rugosa"는 DB에 없지만, "Rosa"로 시작하는 "Rosa canina"가 있음
        result = await plant_repo.find_by_scientific_name_fuzzy("Rosa rugosa")

        assert result is not None
        assert result["name"] == "장미"
        assert result["scientificName"].startswith("Rosa")

    @pytest.mark.asyncio
    async def test_case_insensitive(self, plant_repo: PlantRepository):
        """대소문자 구분 없이 매칭"""
        result = await plant_repo.find_by_scientific_name_fuzzy("LAVANDULA ANGUSTIFOLIA")

        assert result is not None
        assert result["name"] == "라벤더"

    @pytest.mark.asyncio
    async def test_no_match(self, plant_repo: PlantRepository):
        """매칭되는 식물 없음"""
        result = await plant_repo.find_by_scientific_name_fuzzy("Nonexistent species")

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_string(self, plant_repo: PlantRepository):
        """빈 문자열 입력 시 None 반환"""
        result = await plant_repo.find_by_scientific_name_fuzzy("")

        assert result is None

    @pytest.mark.asyncio
    async def test_none_input(self, plant_repo: PlantRepository):
        """None 입력 시 None 반환"""
        result = await plant_repo.find_by_scientific_name_fuzzy(None)

        assert result is None


class TestGetByName:
    """이름 조회 테스트"""

    @pytest.mark.asyncio
    async def test_exact_name_match(self, plant_repo: PlantRepository):
        """정확한 이름 일치"""
        result = await plant_repo.get_by_name("장미")

        assert result is not None
        assert result["name"] == "장미"

    @pytest.mark.asyncio
    async def test_name_not_found(self, plant_repo: PlantRepository):
        """존재하지 않는 이름"""
        result = await plant_repo.get_by_name("존재하지않는꽃")

        assert result is None
