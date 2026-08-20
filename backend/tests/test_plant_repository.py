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
    """키워드 검색 관련도 랭킹: 이름 정확 > 이름 부분 > 꽃말 > 숨은 searchKeywords

    꽃말·searchKeywords 매칭은 substring이 아니라 사전 계산된 searchTokens
    (scripts/build_search_tokens.py 규칙) prefix 매칭. 픽스처의 searchTokens는
    해당 스크립트의 build_tokens() 실제 출력값.
    """

    @pytest.mark.asyncio
    async def test_relevance_order(self, mock_db):
        """이름/꽃말/숨은 키워드 매칭이 관련도 순으로 정렬된다"""
        repo = PlantRepository(mock_db)
        await mock_db.plants.insert_many([
            {"_id": "kw1", "name": "향나무", "flowerInfo": {"language": "인내"}, "searchKeywords": ["향나무"],
             "searchTokens": ["인내", "향나무"]},
            {"_id": "kw2", "name": "나도풍란", "flowerInfo": {"language": "인내"}, "searchKeywords": ["강한 향기"],
             "searchTokens": ["강한 향기", "인내", "향기"]},
            {"_id": "kw3", "name": "국화", "flowerInfo": {"language": "그윽한 향기"}, "searchKeywords": ["국화"],
             "searchTokens": ["국화", "그윽", "그윽한 향기", "향기"]},
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
            {"_id": "e1", "name": "향유", "flowerInfo": {"language": "x"}, "searchKeywords": [], "searchTokens": ["x"]},
            {"_id": "e2", "name": "향", "flowerInfo": {"language": "x"}, "searchKeywords": [], "searchTokens": ["x"]},
        ])
        results = await repo.get_list(keyword="향")
        assert results[0]["name"] == "향"

    @pytest.mark.asyncio
    async def test_match_reason_only_for_hidden_keyword(self, mock_db):
        """이름·꽃말 매칭은 근거 None, 숨은 searchKeywords 매칭만 근거(키워드)를 담는다"""
        repo = PlantRepository(mock_db)
        await mock_db.plants.insert_many([
            {"_id": "m1", "name": "향나무", "flowerInfo": {"language": "인내"}, "searchKeywords": ["향나무"],
             "searchTokens": ["인내", "향나무"]},
            {"_id": "m2", "name": "나도풍란", "flowerInfo": {"language": "인내"}, "searchKeywords": ["강한 향기"],
             "searchTokens": ["강한 향기", "인내", "향기"]},
            {"_id": "m3", "name": "국화", "flowerInfo": {"language": "그윽한 향기"}, "searchKeywords": ["국화"],
             "searchTokens": ["국화", "그윽", "그윽한 향기", "향기"]},
        ])
        by_name = {p["name"]: p for p in await repo.get_list(keyword="향")}
        assert by_name["향나무"].get("match_reason") is None        # 이름 매칭 → 근거 생략
        assert by_name["국화"].get("match_reason") is None          # 꽃말 매칭 → 근거 생략
        assert by_name["나도풍란"].get("match_reason") == "강한 향기"  # 숨은 키워드 → 근거 노출
        # searchKeywords·searchTokens 원본은 응답에 노출되지 않음
        assert "searchKeywords" not in by_name["나도풍란"]
        assert "searchTokens" not in by_name["나도풍란"]


class TestKeywordSubstringMismatch:
    """substring 오매칭 방지: 토큰 prefix 매칭이라 다른 단어 속 우연한 부분열엔 안 걸린다"""

    @pytest.mark.asyncio
    async def test_verb_and_midword_substrings_excluded(self, mock_db):
        """'향' 검색: 향한(동사 활용)·고향(단어 중간)·운향과(과명)는 제외, 향기(명사 어두)는 유지"""
        repo = PlantRepository(mock_db)
        await mock_db.plants.insert_many([
            {"_id": "s1", "name": "날개하늘나리", "flowerInfo": {"language": "하늘을 향한 마음"}, "searchKeywords": [],
             "searchTokens": ["마음", "하늘", "하늘을 향한 마음"]},
            {"_id": "s2", "name": "좀명감나무", "flowerInfo": {"language": "그리운 고향"}, "searchKeywords": [],
             "searchTokens": ["고향", "그리운 고향"]},
            {"_id": "s3", "name": "백선", "flowerInfo": {"language": "인내"}, "searchKeywords": ["운향과"],
             "searchTokens": ["운향과", "인내"]},
            {"_id": "s4", "name": "나도풍란", "flowerInfo": {"language": "인내"}, "searchKeywords": ["강한 향기"],
             "searchTokens": ["강한 향기", "인내", "향기"]},
        ])
        names = [p["name"] for p in await repo.get_list(keyword="향")]
        assert names == ["나도풍란"]

    @pytest.mark.asyncio
    async def test_full_phrase_token_still_searchable(self, mock_db):
        """원문 구문 전체도 토큰이라 '운향과' 직접 검색이나 다어절 prefix 검색은 된다"""
        repo = PlantRepository(mock_db)
        await mock_db.plants.insert_many([
            {"_id": "f1", "name": "백선", "flowerInfo": {"language": "인내"}, "searchKeywords": ["운향과"],
             "searchTokens": ["운향과", "인내"]},
            {"_id": "f2", "name": "나도풍란", "flowerInfo": {"language": "인내"}, "searchKeywords": ["강한 향기"],
             "searchTokens": ["강한 향기", "인내", "향기"]},
        ])
        assert [p["name"] for p in await repo.get_list(keyword="운향과")] == ["백선"]
        assert [p["name"] for p in await repo.get_list(keyword="강한 향기")] == ["나도풍란"]

    @pytest.mark.asyncio
    async def test_regex_special_chars_escaped(self, mock_db):
        """정규식 특수문자가 든 키워드도 리터럴로 안전하게 처리된다"""
        repo = PlantRepository(mock_db)
        await mock_db.plants.insert_many([
            {"_id": "r1", "name": "장미", "flowerInfo": {"language": "사랑"}, "searchKeywords": [],
             "searchTokens": ["사랑"]},
        ])
        # '.'이 와일드카드로 동작하면 전부 매칭되는 회귀를 방지
        assert await repo.get_list(keyword=".*") == []
