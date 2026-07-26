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


class TestKeywordSearchRanking:
    """키워드 검색 관련도 랭킹: 이름 정확 > 이름 부분 > 꽃말 > 숨은 searchKeywords"""

    @pytest.mark.asyncio
    async def test_relevance_order(self, mock_db):
        """이름/꽃말/숨은 키워드 매칭이 관련도 순으로 정렬된다"""
        repo = PlantRepository(mock_db)
        await mock_db.plants.insert_many([
            {"_id": "kw1", "name": "향나무", "flowerInfo": {"language": "인내"}, "searchKeywords": ["향나무"]},
            {"_id": "kw2", "name": "나도풍란", "flowerInfo": {"language": "인내"}, "searchKeywords": ["강한 향기"]},
            {"_id": "kw3", "name": "국화", "flowerInfo": {"language": "그윽한 향기"}, "searchKeywords": ["국화"]},
        ])
        names = [p["name"] for p in await repo.get_list(keyword="향")]
        assert set(names) == {"향나무", "나도풍란", "국화"}
        # 이름 부분일치(향나무) > 꽃말 일치(국화) > 숨은 키워드만(나도풍란)
        assert names.index("향나무") < names.index("국화") < names.index("나도풍란")

    @pytest.mark.asyncio
    async def test_exact_name_ranks_first(self, mock_db):
        """이름 정확 일치가 이름 부분 일치보다 앞선다"""
        repo = PlantRepository(mock_db)
        await mock_db.plants.insert_many([
            {"_id": "e1", "name": "향유", "flowerInfo": {"language": "x"}, "searchKeywords": []},
            {"_id": "e2", "name": "향", "flowerInfo": {"language": "x"}, "searchKeywords": []},
        ])
        results = await repo.get_list(keyword="향")
        assert results[0]["name"] == "향"

    @pytest.mark.asyncio
    async def test_match_reason_only_for_hidden_keyword(self, mock_db):
        """이름·꽃말 매칭은 근거 None, 숨은 searchKeywords 매칭만 근거(키워드)를 담는다"""
        repo = PlantRepository(mock_db)
        await mock_db.plants.insert_many([
            {"_id": "m1", "name": "향나무", "flowerInfo": {"language": "인내"}, "searchKeywords": ["향나무"]},
            {"_id": "m2", "name": "나도풍란", "flowerInfo": {"language": "인내"}, "searchKeywords": ["강한 향기"]},
            {"_id": "m3", "name": "국화", "flowerInfo": {"language": "그윽한 향기"}, "searchKeywords": ["국화"]},
        ])
        by_name = {p["name"]: p for p in await repo.get_list(keyword="향")}
        assert by_name["향나무"].get("match_reason") is None        # 이름 매칭 → 근거 생략
        assert by_name["국화"].get("match_reason") is None          # 꽃말 매칭 → 근거 생략
        assert by_name["나도풍란"].get("match_reason") == "강한 향기"  # 숨은 키워드 → 근거 노출
        # searchKeywords 원본은 응답에 노출되지 않음
        assert "searchKeywords" not in by_name["나도풍란"]
