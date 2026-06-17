"""
Floripedia ETL Pipeline v4
===========================
pykew 기반 전면 리팩토링 — POWO 데이터베이스를 체계적으로 수집

Architecture:
  [pykew POWO] ──→ Integration → Sanitize → Gemini Augment → Validate → JSON

Strategies:
  ornamental — 30개 주요 관상식물 과 전체 수집 (기본)
  korea      — 한국 분포 accepted species
  family     — 특정 과(Family)의 accepted species
  query      — 자유 검색

1. 꽃말 감성 그룹(Flower Groups)
['사랑/고백', '위로/슬픔', '감사/존경', '이별/그리움', '행복/즐거움']

2. 색상 그룹(Color Groups)
['백색/미색', '노랑/주황', '빨강/분홍', '푸른색', '갈색/검정']

3. 식물 분류 그룹(Category Groups)
['꽃과 풀', '나무와 조경', '실내 인테리어', '텃밭과 정원']

4. 향기 그룹(Scent Groups)
['달콤·화사', '싱그러운·시원', '은은·차분', '무향']

5. 세부 색상 라벨 (Color Labels)
['백색', '연두', '초록', '노랑', '빨강', '분홍', '연보라', '보라', '파랑', '하늘', '살구', '갈색', '검정', '다홍', '주황', '미색']

Author: 박주하
"""

import argparse
import glob as _glob
import hashlib
import json
import re
import time
import logging
import sys
import os
from datetime import datetime
from dataclasses import dataclass, field

# --- sys.path 추가 (기존 패턴) ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- .env 연동 (기존 패턴) ---
from dotenv import load_dotenv
load_dotenv()

# --- pykew ---
import pykew.powo as powo
import pykew.core as _pykew_core
from pykew.powo_terms import Name, Geography, Filters

# --- pykew monkey-patch: User-Agent 주입 + URL 최신화 ---
_pykew_core.POWO_URL = "https://powo.science.kew.org/api/2"
powo.API._base_url = _pykew_core.POWO_URL

_MAX_RETRIES_249 = 5

def _patched_get(self, method, params=None, _retry_count=0):
    import requests as _req
    import urllib.parse
    if params is None:
        params = {}
    url = '{base}/{method}?{opt}'.format(
        base=self._base_url, method=method,
        opt=urllib.parse.urlencode(params),
    )
    headers = {"User-Agent": "Floripedia-ETL/4.0 (pykew; +https://github.com)"}
    resp = _req.get(url, headers=headers, timeout=30)
    if resp.status_code == 249:
        if _retry_count >= _MAX_RETRIES_249:
            raise RuntimeError(f"POWO API 249 (Too Many Requests) — {_MAX_RETRIES_249}회 재시도 실패: {url}")
        time.sleep(5 * (_retry_count + 1))
        return _patched_get(self, method, params, _retry_count + 1)
    if resp.status_code >= 400:
        raise RuntimeError(f"POWO API HTTP {resp.status_code}: {url}")
    return resp

_pykew_core.Api.get = _patched_get


# ============================================================
# 1. CONFIG
# ============================================================

class Config:
    GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.5-flash-lite")
    GEMINI_STORY_MODEL = os.getenv("GEMINI_STORY_MODEL", "gemini-2.5-flash")
    OUTPUT_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
    )

    POWO_RATE_LIMIT = 0.3
    GEMINI_RATE_LIMIT = 1.5
    GEMINI_MAX_RETRIES = 3

    CHECKPOINT_INTERVAL = 20  # N건마다 체크포인트 저장

    LOG_LEVEL = logging.INFO


# ============================================================
# 2. EXCEPTIONS
# ============================================================

class DataValidationError(Exception):
    """필수 필드가 비어있을 때 발생"""
    pass


# ============================================================
# 3. DATA MODEL
# ============================================================

SEASONS = {"SPRING", "SUMMER", "FALL", "WINTER"}
STORY_GENRES = {"MYTH", "SCIENCE", "HISTORY", "ART", "EPISODE"}
CATEGORY_GROUPS = {"꽃과 풀", "나무와 조경", "실내 인테리어", "텃밭과 정원"}
SCENT_GROUPS = {"달콤·화사", "싱그러운·시원", "은은·차분", "무향"}
COLOR_GROUPS = {"백색/미색", "노랑/주황", "빨강/분홍", "푸른색", "갈색/검정"}
COLOR_LABELS = {"백색", "연두", "초록", "노랑", "빨강", "분홍", "연보라", "보라", "파랑", "하늘", "살구", "갈색", "검정", "다홍", "주황", "미색"}
FLOWER_GROUPS = {"사랑/고백", "위로/슬픔", "감사/존경", "이별/그리움", "행복/즐거움"}

# 꽃말 키워드 → flowerGroup 강제 매칭 (우선순위 순서)
_FG_KEYWORD_RULES = [
    ("이별/그리움", ["이별", "그리움", "기다림", "추억", "복수", "질투", "미움"]),
    ("위로/슬픔", ["위로", "치유", "고독", "평화", "안식", "보호", "용기", "위험", "독"]),
    ("사랑/고백", ["사랑", "고백", "아름다움", "우아", "신비", "매력", "순수", "청초", "섬세", "애교"]),
    ("감사/존경", ["감사", "존경", "겸손", "고귀", "품위", "숭고", "인내", "강인", "성실", "끈기", "경계", "기사"]),
    ("행복/즐거움", ["행복", "기쁨", "즐거움", "번영", "희망", "축복", "새로운 시작", "기쁜", "봄", "부귀", "자유", "단결"]),
]

# 비규격 colorLabel → 규격 16종 매핑
COLOR_LABEL_MAP = {
    "흰색": "백색", "하얀색": "백색", "하양": "백색", "순백색": "백색",
    "연한 흰색": "백색", "옅은 흰색": "백색", "아주 연한 흰색": "백색",
    "아주 연한 회색빛 흰색": "백색", "연백색": "백색",
    "크림색": "미색", "아이보리": "미색", "아이보리색": "미색", "베이지색": "미색",
    "연미색": "미색", "크림 베이지": "미색", "아주 연한 미색": "미색",
    "연한 녹색빛 미색": "미색", "연한 미색": "미색",
    "노란색": "노랑", "연노랑": "노랑", "연노랑색": "노랑", "밝은 노랑": "노랑",
    "밝은 노란색": "노랑", "선명한 노랑": "노랑", "황금색": "노랑", "금색": "노랑",
    "골드": "노랑", "황금빛 노랑": "노랑", "옅은 노란색": "노랑", "옅은 노랑": "노랑",
    "짙은 노랑": "노랑", "진한 노란색": "노랑", "레몬색": "노랑",
    "연두빛 노랑": "노랑", "황금주황색": "주황",
    "주황색": "주황", "진한 주황": "주황", "밝은 주황": "주황", "붉은 주황": "주황",
    "호박색": "주황", "황갈색": "주황",
    "붉은색": "빨강", "진홍색": "빨강", "선홍색": "빨강", "선명한 붉은색": "빨강",
    "짙은 붉은색": "빨강", "심홍색": "빨강", "벽돌색": "빨강",
    "적갈색": "다홍", "붉은 갈색": "다홍", "붉은갈색": "다홍", "짙은 적갈색": "다홍",
    "자주빛 갈색": "다홍", "자주갈색": "다홍",
    "분홍색": "분홍", "연분홍": "분홍", "연분홍색": "분홍", "진분홍": "분홍",
    "진분홍색": "분홍", "장밋빛 분홍": "분홍", "핫핑크": "분홍", "자홍색": "분홍",
    "자주분홍": "분홍",
    "살구색": "살구",
    "연보라색": "연보라", "연자주색": "연보라", "연자색": "연보라", "연한 보라": "연보라",
    "보라색": "보라", "자주색": "보라", "진보라색": "보라", "진한 보라": "보라",
    "진한 보라색": "보라", "짙은 보라": "보라", "짙은 보라색": "보라",
    "짙은 자주색": "보라", "짙은 남보라": "보라", "짙은 남보라색": "보라",
    "보라남색": "보라", "블루 바이올렛": "보라", "블루바이올렛": "보라",
    "보랏빛 파랑": "보라",
    "파란색": "파랑", "짙은 파랑": "파랑", "진한 파랑": "파랑",
    "선명한 파랑": "파랑", "로얄블루": "파랑", "로얄 블루": "파랑", "로열 블루": "파랑",
    "콘플라워 블루": "파랑", "콘플라워블루": "파랑", "강청색": "파랑", "푸른색": "파랑",
    "하늘색": "하늘", "연하늘색": "하늘", "연한 하늘색": "하늘",
    "스카이블루": "하늘", "스카이 블루": "하늘", "스틸 블루": "하늘", "스틸블루": "하늘",
    "남색": "파랑", "남보라색": "파랑", "남보라": "파랑",
    "청보라색": "보라", "청보라": "보라", "청자색": "보라",
    "슬레이트 블루": "보라", "슬레이트블루": "보라",
    "초록색": "초록", "녹색": "초록", "짙은 녹색": "초록", "진한 녹색": "초록",
    "짙은 초록": "초록", "연녹색": "연두", "연두색": "연두", "옅은 연두색": "연두",
    "연한 황록색": "연두", "황록색": "연두", "연두빛 갈색": "갈색",
    "올리브 그린": "초록", "올리브색": "초록", "올리브 녹색": "초록",
    "짙은 올리브색": "초록", "올리브 갈색": "갈색",
    "연갈색": "갈색", "옅은 갈색": "갈색", "짙은 갈색": "갈색", "어두운 갈색": "갈색",
    "밤색": "갈색", "흙갈색": "갈색", "회갈색": "갈색",
    "회색": "미색", "연회색": "미색", "옅은 회색": "미색",
    "은회색": "미색", "은녹색": "연두", "회녹색": "초록", "연회녹색": "연두",
    "짙은 회녹색": "초록", "청회색": "하늘", "푸른회색": "하늘",
    "청동색": "갈색", "청동빛 녹색": "초록", "청동 녹색": "초록", "청동녹색": "초록",
    "녹갈색": "갈색", "짙은 녹갈색": "갈색", "초록빛 갈색": "갈색",
    "붉은 반점": "빨강", "자주색 반점": "보라",
}

# colorLabel → colorGroup 매핑
COLOR_LABEL_TO_GROUP = {
    "백색": "백색/미색", "미색": "백색/미색",
    "노랑": "노랑/주황", "주황": "노랑/주황", "살구": "노랑/주황",
    "빨강": "빨강/분홍", "분홍": "빨강/분홍", "다홍": "빨강/분홍",
    "연보라": "푸른색", "보라": "푸른색", "파랑": "푸른색", "하늘": "푸른색",
    "연두": "푸른색", "초록": "푸른색",
    "갈색": "갈색/검정", "검정": "갈색/검정",
}

# 필수 필드 — 하나라도 비면 DataValidationError
REQUIRED_FIELDS = [
    "name", "scientific_name", "taxonomy.family",
    "horticulture.category", "horticulture.category_group",
    "horticulture.management", "horticulture.pre_content",
    "flower_info.language", "blooming_months", "season",
]

@dataclass
class Story:
    genre: str = ""
    content: str = ""

@dataclass
class Taxonomy:
    genus: str = ""
    species: str = ""
    family: str = ""

@dataclass
class Horticulture:
    category: str = ""
    category_group: str = ""
    usage: list = field(default_factory=list)
    management: str = ""
    pre_content: str = ""

@dataclass
class ColorInfo:
    hex_codes: list = field(default_factory=list)
    color_labels: list = field(default_factory=list)
    color_group: list = field(default_factory=list)

@dataclass
class ScentInfo:
    scent_tags: list = field(default_factory=list)
    scent_group: list = field(default_factory=list)

@dataclass
class FlowerInfo:
    language: str = ""
    flower_group: str = ""

@dataclass
class PlantDocument:
    """MongoDB 적재용 최종 문서"""

    name: str = ""
    scientific_name: str = ""
    is_representative: bool = True

    taxonomy: Taxonomy = field(default_factory=Taxonomy)
    horticulture: Horticulture = field(default_factory=Horticulture)
    flower_info: FlowerInfo = field(default_factory=FlowerInfo)
    color_info: ColorInfo = field(default_factory=ColorInfo)
    scent_info: ScentInfo = field(default_factory=ScentInfo)

    habitat: str = ""
    stories: list = field(default_factory=list)
    images: list = field(default_factory=list)
    image_url: str = ""

    season: str = ""
    blooming_months: list = field(default_factory=list)
    search_keywords: list = field(default_factory=list)
    popularity_score: int = 0

    _sources: dict = field(default_factory=dict)
    _data_completeness: float = 0.0

    def to_mongo_dict(self) -> dict:
        return {
            "_id": self._deterministic_id(),
            "name": self.name,
            "scientificName": self.scientific_name,
            "isRepresentative": self.is_representative,
            "taxonomy": {
                "genus": self.taxonomy.genus,
                "species": self.taxonomy.species,
                "family": self.taxonomy.family,
            },
            "horticulture": {
                "category": self.horticulture.category,
                "categoryGroup": self.horticulture.category_group,
                "usage": self.horticulture.usage,
                "management": self.horticulture.management,
                "preContent": self.horticulture.pre_content,
            },
            "flowerInfo": {
                "language": self.flower_info.language,
                "flowerGroup": self.flower_info.flower_group,
            },
            "colorInfo": {
                "hexCodes": self.color_info.hex_codes,
                "colorLabels": self.color_info.color_labels,
                "colorGroup": self.color_info.color_group,
            },
            "scentInfo": {
                "scentTags": self.scent_info.scent_tags,
                "scentGroup": self.scent_info.scent_group,
            },
            "habitat": self.habitat,
            "stories": [
                {"genre": s.genre, "content": s.content}
                for s in self.stories if isinstance(s, Story)
            ],
            "images": self.images,
            "imageUrl": self.image_url,
            "season": self.season,
            "bloomingMonths": self.blooming_months,
            "searchKeywords": self.search_keywords,
            "dataCompleteness": self._data_completeness,
        }

    def _deterministic_id(self) -> str:
        """학명 기반 결정적 ID — 동일 식물은 항상 같은 ID"""
        key = self.scientific_name.strip().lower()
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def calculate_completeness(self) -> float:
        checks = [
            bool(self.name),
            bool(self.scientific_name),
            bool(self.taxonomy.genus),
            bool(self.taxonomy.species),
            bool(self.taxonomy.family),
            bool(self.horticulture.category),
            bool(self.horticulture.category_group),
            len(self.horticulture.usage) > 0,
            bool(self.horticulture.management),
            bool(self.horticulture.pre_content),
            bool(self.habitat),
            bool(self.flower_info.language),
            len(self.stories) >= 3,
            bool(self.image_url),
            bool(self.season),
            len(self.blooming_months) > 0,
            len(self.search_keywords) > 0,
            len(self.color_info.hex_codes) > 0,
            len(self.scent_info.scent_tags) > 0,
        ]
        self._data_completeness = round(sum(checks) / len(checks), 3)
        return self._data_completeness

    def validate(self):
        """필수 필드 검증 — 비어있으면 DataValidationError"""
        missing = []
        for path in REQUIRED_FIELDS:
            parts = path.split(".")
            obj = self
            for p in parts:
                obj = getattr(obj, p, None)
                if obj is None:
                    break
            if not obj:
                missing.append(path)
        if missing:
            raise DataValidationError(
                f"[{self.scientific_name}] 필수 필드 누락: {', '.join(missing)}"
            )


# ============================================================
# 4. EXTRACTORS (Kew)
# ============================================================

ORNAMENTAL_FAMILIES = [
    "Rosaceae", "Asteraceae", "Orchidaceae", "Liliaceae", "Iridaceae",
    "Amaryllidaceae", "Paeoniaceae", "Ranunculaceae", "Magnoliaceae", "Hydrangeaceae",
    "Lamiaceae", "Oleaceae",
    "Ericaceae", "Fabaceae", "Theaceae", "Caprifoliaceae",
    "Caryophyllaceae", "Violaceae", "Primulaceae", "Campanulaceae",
    "Balsaminaceae", "Geraniaceae", "Papaveraceae", "Convolvulaceae",
    "Malvaceae", "Solanaceae",
    "Nymphaeaceae", "Nelumbonaceae",
    "Araceae", "Strelitziaceae",
]


class KewExtractor:
    """pykew POWO API → 분류학, 분포, 이미지"""

    def __init__(self, config: Config):
        self.rate_limit = config.POWO_RATE_LIMIT

    def discover_by_distribution(self, region: str, limit: int = 200) -> list:
        logging.info(f"  Discovering plants from region: {region}")
        try:
            result = powo.search(
                {Geography.distribution: region},
                filters=[Filters.accepted, Filters.species],
            )
            items = []
            for item in result:
                items.append(item)
                if len(items) >= limit:
                    break
            logging.info(f"    → {len(items)} species found")
            return items
        except Exception as e:
            logging.error(f"  Distribution search error [{region}]: {e}")
            return []

    def discover_by_family(self, family: str, limit: int = 50,
                           max_per_genus: int = 3) -> list:
        logging.info(f"  Discovering family: {family} (max {max_per_genus}/genus)")
        try:
            result = powo.search(
                {Name.family: family},
                filters=[Filters.accepted, Filters.species],
            )
            items = []
            genus_count: dict[str, int] = {}
            for item in result:
                genus = item.get("name", "").split()[0] if item.get("name") else ""
                if genus:
                    cnt = genus_count.get(genus, 0)
                    if cnt >= max_per_genus:
                        continue
                    genus_count[genus] = cnt + 1
                items.append(item)
                if len(items) >= limit:
                    break
            logging.info(f"    → {len(items)} species from {family} ({len(genus_count)} genera)")
            return items
        except Exception as e:
            logging.error(f"  Family search error [{family}]: {e}")
            return []

    def discover_by_query(self, query: str, limit: int = 50) -> list:
        logging.info(f"  Querying: {query}")
        try:
            result = powo.search(
                {Name.full_name: query},
                filters=[Filters.accepted, Filters.species],
            )
            items = []
            for item in result:
                items.append(item)
                if len(items) >= limit:
                    break
            logging.info(f"    → {len(items)} results for '{query}'")
            return items
        except Exception as e:
            logging.error(f"  Query search error [{query}]: {e}")
            return []

    def discover_all_ornamental(self, limit_per_family: int = 50,
                                total_limit: int = 500,
                                max_per_genus: int = 3) -> list:
        all_items = []
        seen = set()
        for i, family in enumerate(ORNAMENTAL_FAMILIES, 1):
            if len(all_items) >= total_limit:
                logging.info(f"  Reached total limit ({total_limit}), stopping.")
                break
            remaining = total_limit - len(all_items)
            per_family = min(limit_per_family, remaining)
            logging.info(f"  [{i}/{len(ORNAMENTAL_FAMILIES)}] {family} (max {per_family})")
            items = self.discover_by_family(family, limit=per_family,
                                           max_per_genus=max_per_genus)
            for item in items:
                fq_id = item.get("fqId", "")
                if fq_id and fq_id not in seen:
                    seen.add(fq_id)
                    all_items.append(item)
        logging.info(f"  Total ornamental species: {len(all_items)}")
        return all_items

    def lookup_detail(self, fq_id: str) -> dict:
        time.sleep(self.rate_limit)
        try:
            return powo.lookup(fq_id, include=["distribution"])
        except Exception as e:
            logging.error(f"  Lookup error [{fq_id}]: {e}")
            return {}

    def extract(self, raw: dict) -> dict:
        if not raw:
            return {}

        images = raw.get("images", [])
        image_urls = []
        for img in images:
            url = img.get("fullUrl", "") or img.get("url", "")
            if url:
                image_urls.append(url)

        distribution = raw.get("distribution", {})
        natives = distribution.get("natives", [])
        introduced = distribution.get("introduced", [])

        return {
            "scientific_name": raw.get("name", ""),
            "author": raw.get("author", ""),
            "family": raw.get("family", ""),
            "genus": raw.get("genus", ""),
            "fqId": raw.get("fqId", ""),
            "synonyms": [s.get("name", "") for s in raw.get("synonyms", [])],
            "native_distribution": [
                d.get("name", "") for d in natives
            ] if isinstance(natives, list) else [],
            "introduced_distribution": [
                d.get("name", "") for d in introduced
            ] if isinstance(introduced, list) else [],
            "description": (
                raw.get("descriptions", {}).get("description", "")
                if isinstance(raw.get("descriptions"), dict) else ""
            ),
            "images": image_urls,
        }


# ============================================================
# 5. INTEGRATOR
# ============================================================

class DataIntegrator:
    def merge(self, powo_data: dict | None) -> PlantDocument:
        doc = PlantDocument()
        powo_data = powo_data or {}

        doc.scientific_name = powo_data.get("scientific_name") or ""

        doc.taxonomy.genus = powo_data.get("genus") or self._genus(doc.scientific_name)
        doc.taxonomy.species = self._species(doc.scientific_name)
        doc.taxonomy.family = powo_data.get("family") or ""

        native = powo_data.get("native_distribution", [])
        if native:
            doc.habitat = ", ".join(native[:5])

        imgs = powo_data.get("images", [])
        doc.images = imgs[:3]
        doc.image_url = imgs[0] if imgs else ""

        kw = {doc.scientific_name, doc.taxonomy.genus, doc.taxonomy.family}
        doc.search_keywords = [k for k in kw if k]

        doc._sources = {"powo": True}
        return doc

    @staticmethod
    def _genus(s): return s.strip().split()[0] if s else ""
    @staticmethod
    def _species(s):
        p = s.strip().split()
        return p[1] if len(p) >= 2 else ""


# ============================================================
# 6. SANITIZER
# ============================================================

class DataSanitizer:
    HTML_RE = re.compile(r'<[^>]+>')
    CTRL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
    MULTI_SPACE = re.compile(r'\s+')
    FAMILY_SUFFIX = re.compile(r'(과)[에의를은는이가도]')

    def sanitize(self, doc: PlantDocument) -> PlantDocument:
        doc.scientific_name = self._sci_name(doc.scientific_name)
        parts = doc.scientific_name.split()
        doc.taxonomy.genus = parts[0] if parts else ""
        doc.taxonomy.species = parts[1] if len(parts) >= 2 else ""

        doc.taxonomy.family = self._family(doc.taxonomy.family)

        doc.name = self._t(doc.name)
        # habitat: "원산지: " 접두사 제거
        h = self._t(doc.habitat)
        if h.startswith("원산지: "):
            h = h[len("원산지: "):]
        elif h.startswith("원산지:"):
            h = h[len("원산지:"):]
        doc.habitat = h[:500]
        doc.horticulture.management = self._t(doc.horticulture.management)[:2000]
        doc.horticulture.pre_content = self._t(doc.horticulture.pre_content)[:1000]
        doc.horticulture.category = self._t(doc.horticulture.category)
        doc.flower_info.language = self._t(doc.flower_info.language)

        doc.horticulture.usage = [u for u in doc.horticulture.usage if u.strip()]
        doc.search_keywords = list(set(k.strip() for k in doc.search_keywords if k.strip()))

        # scentTags: "향 없음" → "무향" 통일
        doc.scent_info.scent_tags = [
            "무향" if t.strip() == "향 없음" else t
            for t in doc.scent_info.scent_tags if t.strip()
        ]

        doc.color_info.hex_codes = [
            h for h in doc.color_info.hex_codes if re.match(r'^#[0-9A-Fa-f]{6}$', h)
        ]

        # colorLabels: 비규격 → 규격 16종 매핑 + 중복 제거
        mapped_labels = []
        for lbl in doc.color_info.color_labels:
            if lbl in COLOR_LABELS:
                mapped_labels.append(lbl)
            elif lbl in COLOR_LABEL_MAP:
                mapped_labels.append(COLOR_LABEL_MAP[lbl])
            # 매핑 없는 비규격은 버림
        seen_labels = set()
        deduped_labels = []
        for lbl in mapped_labels:
            if lbl not in seen_labels:
                seen_labels.add(lbl)
                deduped_labels.append(lbl)
        doc.color_info.color_labels = deduped_labels

        # colorGroup: colorLabels 기반 재매핑
        new_groups = []
        for lbl in doc.color_info.color_labels:
            if lbl in COLOR_LABEL_TO_GROUP:
                g = COLOR_LABEL_TO_GROUP[lbl]
                if g not in new_groups:
                    new_groups.append(g)
        if new_groups:
            doc.color_info.color_group = new_groups
        else:
            doc.color_info.color_group = [g for g in doc.color_info.color_group if g in COLOR_GROUPS]

        # hex↔label 1:1: hex가 더 많으면 label 수에 맞춰 자름
        if (len(doc.color_info.hex_codes) > len(doc.color_info.color_labels)
                and len(doc.color_info.color_labels) > 0):
            doc.color_info.hex_codes = doc.color_info.hex_codes[:len(doc.color_info.color_labels)]

        # enum/그룹 검증
        if doc.horticulture.category_group not in CATEGORY_GROUPS:
            doc.horticulture.category_group = ""

        # flowerGroup: 꽃말 키워드 매칭 우선 → 안 걸리면 Gemini 값 사용
        fg = self._match_flower_group_by_keyword(doc.flower_info.language)
        if fg == "행복/즐거움":
            # 키워드 기본값일 수 있으므로 Gemini 값 확인
            gemini_fg = self._match_group(doc.flower_info.flower_group, FLOWER_GROUPS, "")
            if gemini_fg and gemini_fg != "기타" and gemini_fg != "행복/즐거움":
                fg = gemini_fg
        doc.flower_info.flower_group = fg

        if doc.season not in SEASONS:
            doc.season = "SPRING"

        doc.blooming_months = sorted(set(
            int(m) for m in doc.blooming_months
            if isinstance(m, (int, float, str)) and str(m).strip().isdigit()
            and 1 <= int(m) <= 12
        ))

        doc.stories = [
            Story(genre=s.genre, content=self._t(s.content)[:300])
            for s in doc.stories
            if isinstance(s, Story) and s.genre in STORY_GENRES and s.content
        ][:5]

        # scentGroup: "향 없음" → "무향" 통일
        doc.scent_info.scent_group = [
            "무향" if g == "향 없음" else g
            for g in doc.scent_info.scent_group if g in SCENT_GROUPS or g == "향 없음"
        ]
        if not doc.scent_info.scent_group:
            doc.scent_info.scent_group = ["은은·차분"] if doc.scent_info.scent_tags else ["무향"]

        # 무향인데 scentTags 비어있으면 ["무향"] 삽입
        if not doc.scent_info.scent_tags and "무향" in doc.scent_info.scent_group:
            doc.scent_info.scent_tags = ["무향"]

        # season: blooming_months 기반 다수결
        if doc.blooming_months:
            doc.season = self._calc_season(doc.blooming_months)

        doc.calculate_completeness()
        return doc

    @staticmethod
    def _calc_season(months: list) -> str:
        sm = {12: "WINTER", 1: "WINTER", 2: "WINTER",
              3: "SPRING", 4: "SPRING", 5: "SPRING",
              6: "SUMMER", 7: "SUMMER", 8: "SUMMER",
              9: "FALL", 10: "FALL", 11: "FALL"}
        cnt = {}
        for m in months:
            s = sm.get(m, "SPRING")
            cnt[s] = cnt.get(s, 0) + 1
        last = sm.get(max(months), "SPRING")
        return max(cnt, key=lambda s: (cnt[s], s == last))

    @staticmethod
    def _match_flower_group_by_keyword(language: str) -> str:
        """꽃말 텍스트에서 키워드 매칭으로 flowerGroup 강제 분류"""
        if not language:
            return "행복/즐거움"
        for group, keywords in _FG_KEYWORD_RULES:
            for kw in keywords:
                if kw in language:
                    return group
        return "행복/즐거움"

    @staticmethod
    def _match_group(value: str, valid_set: set, default: str) -> str:
        """정확히 일치하면 그대로, 아니면 포함 관계로 매칭 시도"""
        if not value:
            return default
        value = value.strip()
        if value in valid_set:
            return value
        # "사랑" → "사랑/고백", "고백" → "사랑/고백" 등 부분 매칭
        for candidate in valid_set:
            parts = candidate.split("/")
            if value in parts or value == candidate.replace("/", ""):
                return candidate
        return default

    def _t(self, text):
        if not text:
            return ""
        text = self.HTML_RE.sub('', text)
        text = self.CTRL_RE.sub('', text)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return self.MULTI_SPACE.sub(' ', text).strip()

    def _sci_name(self, n):
        if not n:
            return ""
        p = n.strip().split()
        if len(p) >= 2:
            p[0], p[1] = p[0].capitalize(), p[1].lower()
        elif p:
            p[0] = p[0].capitalize()
        return " ".join(p)

    def _family(self, f):
        if not f:
            return ""
        f = self._t(f)
        return self.FAMILY_SUFFIX.sub(r'\1', f)


# ============================================================
# 7. GEMINI AUGMENTER
# ============================================================

class GeminiAugmenter:
    def __init__(self, config: Config):
        self.api_key = config.GEMINI_API_KEY
        self.base_url = config.GEMINI_API_BASE
        self.model = config.GEMINI_MODEL
        self.story_model = config.GEMINI_STORY_MODEL
        self.rate_limit = config.GEMINI_RATE_LIMIT
        self.max_retries = config.GEMINI_MAX_RETRIES

        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")

    def augment(self, doc: PlantDocument) -> PlantDocument:
        base = self._gen_base(doc)
        if not base:
            raise DataValidationError(
                f"[{doc.scientific_name}] Gemini _gen_base 응답 파싱 실패 — 빈 dict 반환"
            )

        if not doc.name:
            doc.name = base.get("name", "")
        if not self._kor(doc.taxonomy.family):
            doc.taxonomy.family = base.get("family_ko", doc.taxonomy.family)
        if not doc.horticulture.category:
            doc.horticulture.category = base.get("category", "")
        if not doc.horticulture.category_group:
            doc.horticulture.category_group = base.get("category_group", "")
        if not doc.horticulture.pre_content:
            doc.horticulture.pre_content = base.get("pre_content", "")
        if not doc.horticulture.management:
            doc.horticulture.management = base.get("management", "")
        if not doc.horticulture.usage:
            doc.horticulture.usage = base.get("usage", [])
        if not doc.flower_info.language:
            doc.flower_info.language = base.get("flower_language", "")
        if not doc.flower_info.flower_group or doc.flower_info.flower_group == "기타":
            doc.flower_info.flower_group = base.get("flower_group", "기타")
        if not doc.color_info.hex_codes:
            doc.color_info.hex_codes = base.get("hex_codes", [])
            doc.color_info.color_labels = base.get("color_labels", [])
            doc.color_info.color_group = base.get("color_group", [])
        if not doc.scent_info.scent_tags:
            doc.scent_info.scent_tags = base.get("scent_tags", [])
        sg = base.get("scent_group", [])
        if sg:
            doc.scent_info.scent_group = sg
        if not doc.blooming_months:
            doc.blooming_months = base.get("blooming_months", [])
        if doc.blooming_months:
            doc.season = self._season(doc.blooming_months)

        # Stories
        if len(doc.stories) < 3:
            stories = self._gen_stories(doc)
            if not stories:
                raise DataValidationError(
                    f"[{doc.scientific_name}] Stories 생성 실패 — Gemini 응답 파싱 불가"
                )
            doc.stories = stories

        # 한글 키워드
        for kw in [doc.name, doc.taxonomy.family, doc.flower_info.language]:
            if kw and kw not in doc.search_keywords:
                doc.search_keywords.append(kw)

        return doc

    @staticmethod
    def _season(months: list) -> str:
        if not months:
            return "SPRING"
        sm = {12: "WINTER", 1: "WINTER", 2: "WINTER",
              3: "SPRING", 4: "SPRING", 5: "SPRING",
              6: "SUMMER", 7: "SUMMER", 8: "SUMMER",
              9: "FALL", 10: "FALL", 11: "FALL"}
        counts = {}
        for m in months:
            s = sm.get(m, "SPRING")
            counts[s] = counts.get(s, 0) + 1
        last_season = sm.get(max(months), "SPRING")
        return max(counts, key=lambda s: (counts[s], s == last_season))

    def _gen_base(self, doc: PlantDocument) -> dict:
        habitat_ctx = doc.habitat[:200] if doc.habitat else ""

        prompt = f"""당신은 식물학 전문가이자 원예 상담사입니다. 다음 식물의 정보를 JSON으로 생성하세요.

학명: {doc.scientific_name}
과(영문): {doc.taxonomy.family}
서식지: {habitat_ctx}

JSON 형식으로만 응답:
{{
  "name": "한글 이름",
  "family_ko": "과 한글명 (예: 꿀풀과, 장미과)",
  "category": "화훼 부류 (예: 조경수목, 일년초, 숙근초, 관엽식물)",
  "category_group": "꽃과 풀 / 나무와 조경 / 실내 인테리어 / 텃밭과 정원 중 하나",
  "usage": ["용도를 한글로 (예: 관상용, 식용, 약용, 향료, 조경 등)"],
  "pre_content": "이 식물의 매력을 담은 감성적 한글 설명 (150-250자)",
  "management": "구체적 관리법 한글 서술. 물주기(빈도/방법), 햇빛(광량/위치), 전정(시기/방법), 토양, 월동 요령을 포함하여 200-400자로 작성",
  "flower_language": "꽃말 (한글)",
  "flower_group": "사랑/고백 / 위로/슬픔 / 감사/존경 / 이별/그리움 / 행복/즐거움 중 하나 (기타 금지)",
  "hex_codes": ["#XXXXXX", "#XXXXXX"],
  "color_labels": ["반드시 다음 중 선택: 백색, 연두, 초록, 노랑, 빨강, 분홍, 연보라, 보라, 파랑, 하늘, 살구, 갈색, 검정, 다홍, 주황, 미색"],
  "color_group": ["백색/미색 / 노랑/주황 / 빨강/분홍 / 푸른색 / 갈색/검정 중 해당"],
  "scent_tags": ["향기 묘사 한글 (예: 달콤한, 장미향, 상쾌한). 무향이면 [무향]"],
  "scent_group": ["달콤·화사 / 싱그러운·시원 / 은은·차분 / 무향 중 해당"],
  "blooming_months": [3, 4, 5]
}}"""
        result = self._call(prompt, max_tokens=8000)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            logging.error(f"  Gemini JSON 파싱 실패 [{doc.scientific_name}]: {result[:200]}")
            return {}

    def _gen_stories(self, doc: PlantDocument) -> list:
        prompt = f"""식물학 전문가로서 다음 식물에 관한 **사실에 근거한** 이야기를 작성하세요.

식물: {doc.name or doc.scientific_name}
학명: {doc.scientific_name}
과: {doc.taxonomy.family}
꽃말: {doc.flower_info.language}
서식지: {doc.habitat[:150]}

규칙:
1. 반드시 사실에 근거한 이야기만 작성 (창작·지어낸 전설 금지)
2. 이 식물과 연관도 또는 매력도가 높은 순서로 5개 선정
3. 각 이야기에 가장 적합한 장르 태그 1개 부여 (MYTH / SCIENCE / HISTORY / ART / EPISODE)
4. 장르 중복 가능 (예: SCIENCE 3개도 OK)
5. 각 스토리 200자 이내 엄격 제한 (200자 초과 절대 금지)

JSON 배열만 응답:
[
  {{"genre": "장르태그", "content": "사실 기반 이야기 (200자 이내)"}},
  ...
]"""
        result = self._call(prompt, max_tokens=16000, model=self.story_model)
        try:
            parsed = json.loads(result)
            # Gemini가 객체로 감싸는 경우: {"stories": [...]} 등
            if isinstance(parsed, dict):
                for v in parsed.values():
                    if isinstance(v, list):
                        parsed = v
                        break
                else:
                    logging.error(f"  Stories 응답이 dict이나 list 값 없음 [{doc.scientific_name}]: {str(parsed)[:200]}")
                    return []
            if not isinstance(parsed, list):
                logging.error(f"  Stories 응답 타입 비정상 [{doc.scientific_name}]: {type(parsed)}")
                return []
            return [
                Story(genre=s["genre"], content=s["content"])
                for s in parsed
                if isinstance(s, dict) and s.get("genre") in STORY_GENRES and s.get("content")
            ][:5]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logging.error(f"  Stories JSON 파싱 실패 [{doc.scientific_name}]: {e} — 응답: {str(result)[:200]}")
            return []

    def _call(self, prompt: str, max_tokens: int = 4000, model: str = None) -> str:
        import requests
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            time.sleep(self.rate_limit)
            try:
                use_model = model or self.model
                resp = requests.post(
                    f"{self.base_url}/models/{use_model}:generateContent",
                    params={"key": self.api_key},
                    json=payload,
                    timeout=60,
                )
                resp.raise_for_status()
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                last_error = e
                logging.warning(f"  Gemini attempt {attempt}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.rate_limit * attempt * 2)

        raise RuntimeError(
            f"Gemini API {self.max_retries}회 재시도 모두 실패: {last_error}"
        )

    @staticmethod
    def _kor(t):
        return bool(t and re.search(r'[가-힣]', t))


# ============================================================
# 8. PIPELINE ORCHESTRATOR
# ============================================================

class FloripediaETL:
    def __init__(self, config: Config = None, args: argparse.Namespace = None):
        self.config = config or Config()
        self.args = args
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.kew = KewExtractor(self.config)
        self.integrator = DataIntegrator()
        self.sanitizer = DataSanitizer()
        self.augmenter = GeminiAugmenter(self.config)

        # augment 진행 중 체크포인트용 (BUG 1 fix)
        self._augmented_so_far: list[PlantDocument] = []

        # 통계 수집
        self.stats = {
            "discover": 0,
            "lookup_ok": 0,
            "lookup_fail": 0,
            "gemini_ok": 0,
            "gemini_fail": 0,
            "dedup_removed": 0,
        }

        logging.basicConfig(
            level=self.config.LOG_LEVEL,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )

    def run(self):
        strategy = self.args.strategy if self.args else "ornamental"
        total_limit = self.args.total_limit if self.args else 500
        limit_per_family = self.args.limit_per_family if self.args else 50
        max_per_genus = self.args.max_per_genus if self.args else 3
        images_only = self.args.images_only if self.args else False
        append_mode = self.args.append if self.args else False
        trim_genus = self.args.trim_genus if self.args else 0

        logging.info("=" * 60)
        logging.info(f"Floripedia ETL v4 (pykew) — {self.run_id}")
        logging.info(f"Strategy: {strategy} | Limit: {total_limit} | MaxPerGenus: {max_per_genus}")
        if append_mode:
            logging.info(f"Mode: APPEND (기존 데이터에 추가)")
        if trim_genus:
            logging.info(f"Trim: 속당 {trim_genus}건 초과 삭제")
        logging.info("=" * 60)
        start = time.time()

        # --trim-genus: 수집 없이 기존 데이터 정리만
        if trim_genus and not append_mode:
            output_path = os.path.join(self.config.OUTPUT_DIR, "v2_data_patched.json")
            if os.path.exists(output_path):
                trimmed_docs = self._trim_existing_by_genus(output_path, trim_genus)
                # 재정리
                trimmed_docs = [self.sanitizer.sanitize(d) for d in trimmed_docs]
                self._fill_missing_habitat(trimmed_docs)
                out = self._save_json(trimmed_docs)
                elapsed = round(time.time() - start, 1)
                logging.info(f"Trim 완료: {len(trimmed_docs)}건 → {out} ({elapsed}s)")
                return {"count": len(trimmed_docs), "output": out, "elapsed": elapsed}
            else:
                raise RuntimeError(f"Trim 대상 파일 없음: {output_path}")

        # DB 데이터(added_images.json) 학명 로드 — 항상 중복 방지
        existing_names: set[str] = set()
        db_path = os.path.join(self.config.OUTPUT_DIR, "added_images.json")
        if os.path.exists(db_path):
            with open(db_path, "r", encoding="utf-8") as f:
                db_plants = json.load(f)
            for p in db_plants:
                sci = p.get("scientificName", "").strip().lower()
                if sci:
                    existing_names.add(sci)
            logging.info(f"  DB 학명 로드: {len(existing_names)}종 (중복 방지)")

        # 기존 ETL 데이터 로드 (append 모드)
        existing_docs: list[PlantDocument] = []
        existing_genera: dict[str, int] = {}
        if append_mode:
            output_path = os.path.join(self.config.OUTPUT_DIR, "v2_data_patched.json")
            if os.path.exists(output_path):
                existing_docs, etl_names = self._load_checkpoint(output_path)
                existing_names |= etl_names
                for d in existing_docs:
                    g = d.taxonomy.genus
                    existing_genera[g] = existing_genera.get(g, 0) + 1
                logging.info(f"  기존 ETL 데이터: {len(existing_docs)}건, {len(existing_genera)}개 속")
            else:
                logging.info("  기존 파일 없음 — 새로 수집")

        try:
            # 1. Discover
            logging.info("[1] Discovering plants via pykew...")
            search_results = self._discover(strategy, total_limit, limit_per_family,
                                            max_per_genus)
            self.stats["discover"] = len(search_results)
            logging.info(f"    → {len(search_results)} candidate species")

            if not search_results:
                raise RuntimeError("검색 결과 0건 — POWO API 또는 전략을 확인하세요.")

            # 2. Lookup + Extract (기존 학명 스킵)
            logging.info("[2] Looking up details & extracting...")
            raw_entries = self._lookup_and_extract(
                search_results, images_only,
                exclude_names=existing_names,
                genus_counts=dict(existing_genera) if append_mode else {},
                max_per_genus=max_per_genus if append_mode else 0,
            )
            logging.info(
                f"    → {len(raw_entries)} plants with data "
                f"(lookup 성공: {self.stats['lookup_ok']}, "
                f"실패: {self.stats['lookup_fail']})"
            )

            if not raw_entries:
                if append_mode and existing_docs:
                    logging.info("  새 식물 없음 — 기존 데이터 유지")
                    output_path = self._save_json(existing_docs)
                    elapsed = round(time.time() - start, 1)
                    return {"count": len(existing_docs), "output": output_path, "elapsed": elapsed}
                raise RuntimeError("lookup 결과 0건 — POWO API 응답을 확인하세요.")

            # 3. Integrate
            logging.info("[3] Integrating (Kew → PlantDocument)...")
            docs = self._integrate(raw_entries)

            # 4. Sanitize
            logging.info("[4] Sanitizing...")
            docs = [self.sanitizer.sanitize(d) for d in docs]

            # 5. Gemini Augment + Validate (with checkpoint)
            logging.info("[5] Gemini augmenting + validating...")
            completed_docs = self._augment_with_checkpoint(docs)

            # 6. Final sanitize
            logging.info("[6] Final sanitize...")
            completed_docs = [self.sanitizer.sanitize(d) for d in completed_docs]

            # Append: 기존 + 신규 병합
            if append_mode and existing_docs:
                completed_docs = existing_docs + completed_docs
                logging.info(f"  병합: 기존 {len(existing_docs)} + 신규 {len(completed_docs) - len(existing_docs)} = {len(completed_docs)}건")

            # 7. Post-process: habitat 누락 → 같은 속 참조
            logging.info("[7] Post-process (habitat gap fill)...")
            self._fill_missing_habitat(completed_docs)

            # 8. Save
            output_path = self._save_json(completed_docs)

            elapsed = round(time.time() - start, 1)
            self._log_summary(completed_docs, output_path, elapsed)
            return {"count": len(completed_docs), "output": output_path, "elapsed": elapsed}

        except (DataValidationError, RuntimeError) as e:
            logging.error(f"PIPELINE ERROR: {e}")
            saved = self._augmented_so_far
            if saved:
                cp = self._save_checkpoint(saved, "error")
                logging.error(f"  체크포인트 저장 완료: {cp} ({len(saved)}건)")
            else:
                logging.error("  저장할 데이터 없음.")
            sys.exit(1)

        except KeyboardInterrupt:
            logging.warning("사용자 중단 (Ctrl+C)")
            saved = self._augmented_so_far
            if saved:
                cp = self._save_checkpoint(saved, "interrupted")
                logging.warning(f"  체크포인트 저장 완료: {cp} ({len(saved)}건)")
            sys.exit(130)

        except Exception as e:
            logging.error(f"UNEXPECTED ERROR: {type(e).__name__}: {e}")
            saved = self._augmented_so_far
            if saved:
                cp = self._save_checkpoint(saved, "crash")
                logging.error(f"  체크포인트 저장 완료: {cp} ({len(saved)}건)")
            raise

    def _augment_with_checkpoint(self, docs: list) -> list:
        """Gemini 증강 + 검증 + 주기적 체크포인트 + 이어하기"""
        self._augmented_so_far = []
        resumed_seen: set[str] = set()

        # --resume: 체크포인트에서 이미 처리된 식물 불러오기
        resume = self.args.resume if self.args else None
        if resume:
            if resume == "auto":
                cp_path = self._find_latest_checkpoint()
                if not cp_path:
                    logging.warning("  체크포인트 파일 없음 — 처음부터 시작합니다.")
                else:
                    resume = cp_path
            if resume and resume != "auto":
                loaded_docs, resumed_seen = self._load_checkpoint(resume)
                self._augmented_so_far.extend(loaded_docs)
                logging.info(f"  → {len(loaded_docs)}건 이어하기, {len(docs)}건 중 스킵 예정")

        total = len(docs)
        interval = self.config.CHECKPOINT_INTERVAL
        processed = 0

        for i, doc in enumerate(docs, 1):
            sci_key = doc.scientific_name.strip().lower()
            if sci_key in resumed_seen:
                logging.debug(f"  [{i}/{total}] SKIP (체크포인트) {doc.scientific_name}")
                continue

            processed += 1
            logging.info(f"  [{i}/{total}] {doc.scientific_name}")

            try:
                doc = self.augmenter.augment(doc)
                self.stats["gemini_ok"] += 1
                doc = self.sanitizer.sanitize(doc)
                doc.validate()
            except (DataValidationError, RuntimeError) as e:
                self.stats["gemini_fail"] += 1
                logging.warning(f"    SKIP: {e}")
                continue

            self._augmented_so_far.append(doc)

            # 주기적 체크포인트
            if processed % interval == 0:
                cp = self._save_checkpoint(self._augmented_so_far, f"progress_{i}")
                logging.info(f"    checkpoint: {cp} ({len(self._augmented_so_far)}건)")

        return self._augmented_so_far

    def _discover(self, strategy: str, total_limit: int, limit_per_family: int,
                  max_per_genus: int = 3) -> list:
        if strategy == "korea":
            return self.kew.discover_by_distribution("Korea", limit=total_limit)
        elif strategy == "family":
            family = self.args.family if self.args else "Rosaceae"
            return self.kew.discover_by_family(family, limit=total_limit,
                                               max_per_genus=max_per_genus)
        elif strategy == "query":
            query = self.args.query if self.args else ""
            return self.kew.discover_by_query(query, limit=total_limit)
        else:
            return self.kew.discover_all_ornamental(
                limit_per_family=limit_per_family,
                total_limit=total_limit,
                max_per_genus=max_per_genus,
            )

    def _lookup_and_extract(self, search_results: list, images_only: bool,
                            exclude_names: set = None,
                            genus_counts: dict = None,
                            max_per_genus: int = 0) -> list:
        entries = []
        seen_fqid = set()
        seen_name = set(exclude_names or set())
        g_counts = dict(genus_counts or {})
        total = len(search_results)
        skipped_existing = 0
        skipped_genus = 0

        for i, item in enumerate(search_results, 1):
            fq_id = item.get("fqId", "")
            if not fq_id or fq_id in seen_fqid:
                continue
            seen_fqid.add(fq_id)

            # 빠른 스킵: 이미 존재하는 학명
            item_name = item.get("name", "").strip().lower()
            if item_name and item_name in seen_name:
                skipped_existing += 1
                continue

            # append 모드 genus 제한: 기존+신규 합산
            if max_per_genus > 0 and item_name:
                genus = item_name.split()[0] if item_name else ""
                if genus and g_counts.get(genus, 0) >= max_per_genus:
                    skipped_genus += 1
                    continue

            if i % 10 == 0 or i == 1:
                logging.info(f"    [{i}/{total}] {item.get('name', '?')}")

            detail = self.kew.lookup_detail(fq_id)
            if not detail:
                self.stats["lookup_fail"] += 1
                continue
            self.stats["lookup_ok"] += 1

            kew_data = self.kew.extract(detail)
            if not kew_data:
                continue

            if images_only and not kew_data.get("images"):
                continue

            # 학명 기반 중복 제거
            sci = kew_data.get("scientific_name", "").strip().lower()
            if sci in seen_name:
                self.stats["dedup_removed"] += 1
                continue
            seen_name.add(sci)

            # genus 카운트 갱신
            genus = sci.split()[0] if sci else ""
            if genus:
                g_counts[genus] = g_counts.get(genus, 0) + 1

            entries.append({
                "name": kew_data.get("scientific_name", ""),
                "kew_data": kew_data,
            })

        if skipped_existing:
            logging.info(f"    → 기존 데이터 중복 스킵: {skipped_existing}건")
        if skipped_genus:
            logging.info(f"    → 속(genus) 초과 스킵: {skipped_genus}건")

        return entries

    def _integrate(self, raw_entries: list) -> list:
        docs = []
        for e in raw_entries:
            kew_data = e.get("kew_data")
            doc = self.integrator.merge(kew_data)
            if not doc.scientific_name:
                doc.scientific_name = e["name"]
            docs.append(doc)
        return docs

    @staticmethod
    def _fill_missing_habitat(docs: list) -> int:
        """habitat이 비어있는 식물을 같은 속(genus) 식물 참고해서 채움"""
        from collections import Counter as _Counter
        genus_habitats: dict[str, list[str]] = {}
        for d in docs:
            if d.habitat and d.taxonomy.genus:
                genus_habitats.setdefault(d.taxonomy.genus, []).append(d.habitat)
        filled = 0
        for d in docs:
            if d.habitat or not d.taxonomy.genus:
                continue
            candidates = genus_habitats.get(d.taxonomy.genus, [])
            if candidates:
                d.habitat = _Counter(candidates).most_common(1)[0][0]
                filled += 1
                logging.info(f"  habitat 채움: {d.name or d.scientific_name} → {d.habitat}")
        return filled

    def _save_json(self, docs: list[PlantDocument]) -> str:
        os.makedirs(self.config.OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(self.config.OUTPUT_DIR, "v2_data_patched.json")
        plants = [d.to_mongo_dict() for d in docs]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(plants, f, ensure_ascii=False, indent=2)
        logging.info(f"[8] Saved {len(plants)} plants → {output_path}")
        return output_path

    def _save_checkpoint(self, docs: list[PlantDocument], tag: str) -> str:
        os.makedirs(self.config.OUTPUT_DIR, exist_ok=True)
        path = os.path.join(
            self.config.OUTPUT_DIR,
            f"checkpoint_{self.run_id}_{tag}.json",
        )
        plants = [d.to_mongo_dict() for d in docs]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(plants, f, ensure_ascii=False, indent=2)
        return path

    def _find_latest_checkpoint(self) -> str | None:
        """data/ 디렉토리에서 타임스탬프가 가장 큰 checkpoint 파일 반환"""
        pattern = os.path.join(self.config.OUTPUT_DIR, "checkpoint_*.json")
        files = _glob.glob(pattern)
        if not files:
            return None
        # 파일명의 타임스탬프 부분(checkpoint_YYYYMMDD_HHMMSS_...)으로 정렬
        files.sort(key=lambda f: os.path.basename(f), reverse=True)
        return files[0]

    def _load_checkpoint(self, path: str) -> tuple[list[PlantDocument], set[str]]:
        """체크포인트 JSON → (PlantDocument 리스트, 이미 처리된 학명 set)"""
        with open(path, "r", encoding="utf-8") as f:
            plants = json.load(f)
        logging.info(f"  체크포인트 로드: {path} ({len(plants)}건)")

        docs = []
        seen = set()
        for p in plants:
            doc = PlantDocument()
            doc.name = p.get("name", "")
            doc.scientific_name = p.get("scientificName", "")
            doc.is_representative = p.get("isRepresentative", True)

            tax = p.get("taxonomy", {})
            doc.taxonomy = Taxonomy(
                genus=tax.get("genus", ""),
                species=tax.get("species", ""),
                family=tax.get("family", ""),
            )

            hort = p.get("horticulture", {})
            doc.horticulture = Horticulture(
                category=hort.get("category", ""),
                category_group=hort.get("categoryGroup", ""),
                usage=hort.get("usage", []),
                management=hort.get("management", ""),
                pre_content=hort.get("preContent", ""),
            )

            fi = p.get("flowerInfo", {})
            doc.flower_info = FlowerInfo(
                language=fi.get("language", ""),
                flower_group=fi.get("flowerGroup", ""),
            )

            ci = p.get("colorInfo", {})
            doc.color_info = ColorInfo(
                hex_codes=ci.get("hexCodes", []),
                color_labels=ci.get("colorLabels", []),
                color_group=ci.get("colorGroup", []),
            )

            si = p.get("scentInfo", {})
            doc.scent_info = ScentInfo(
                scent_tags=si.get("scentTags", []),
                scent_group=si.get("scentGroup", []),
            )

            doc.habitat = p.get("habitat", "")
            doc.stories = [
                Story(genre=s.get("genre", ""), content=s.get("content", ""))
                for s in p.get("stories", [])
            ]
            doc.images = p.get("images", [])
            doc.image_url = p.get("imageUrl", "")
            doc.season = p.get("season", "")
            doc.blooming_months = p.get("bloomingMonths", [])
            doc.search_keywords = p.get("searchKeywords", [])
            doc._data_completeness = p.get("dataCompleteness", 0.0)

            docs.append(doc)
            seen.add(doc.scientific_name.strip().lower())

        return docs, seen

    def _trim_existing_by_genus(self, path: str, max_per: int) -> list[PlantDocument]:
        """기존 데이터에서 속당 max_per건만 남기고 삭제 (dataCompleteness 높은 순 유지)"""
        docs, _ = self._load_checkpoint(path)
        # 속별로 그룹핑 → completeness 내림차순 정렬 → 상위 N개만
        from collections import defaultdict
        genus_groups: dict[str, list[PlantDocument]] = defaultdict(list)
        for d in docs:
            genus_groups[d.taxonomy.genus].append(d)

        kept = []
        removed = 0
        for genus, group in genus_groups.items():
            group.sort(key=lambda d: d._data_completeness, reverse=True)
            kept.extend(group[:max_per])
            removed += max(0, len(group) - max_per)
            if len(group) > max_per:
                logging.info(f"  {genus}: {len(group)}→{max_per} (completeness 기준)")

        logging.info(f"  Trim: {len(docs)}건 → {len(kept)}건 (속당 max {max_per}, {removed}건 삭제)")
        return kept

    def _log_summary(self, docs: list[PlantDocument], output_path: str, elapsed: float):
        count = len(docs)
        logging.info("=" * 60)
        logging.info(f"PIPELINE COMPLETE — {elapsed}s")
        logging.info(f"  Output    : {output_path}")
        logging.info(f"  Plants    : {count}")
        logging.info(f"  Discover  : {self.stats['discover']}")
        logging.info(f"  Lookup    : {self.stats['lookup_ok']} ok / {self.stats['lookup_fail']} fail")
        logging.info(f"  Gemini    : {self.stats['gemini_ok']} ok")
        logging.info(f"  Dedup     : {self.stats['dedup_removed']} removed")
        if count > 0:
            completeness = [d._data_completeness for d in docs]
            avg_c = round(sum(completeness) / len(completeness), 3)
            min_c = min(completeness)
            max_c = max(completeness)
            logging.info(f"  Completeness: avg={avg_c}, min={min_c}, max={max_c}")
        logging.info("=" * 60)


# ============================================================
# 9. CLI ENTRY POINT
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Floripedia ETL v4 — pykew 기반 식물 데이터 수집 파이프라인",
    )
    parser.add_argument(
        "--strategy",
        choices=["ornamental", "korea", "family", "query"],
        default="ornamental",
        help="수집 전략 (기본: ornamental)",
    )
    parser.add_argument(
        "--family", type=str, default="Rosaceae",
        help="family 전략 시 과명 (e.g. Rosaceae)",
    )
    parser.add_argument(
        "--query", type=str, default="",
        help="query 전략 시 검색어 (e.g. Lavandula)",
    )
    parser.add_argument(
        "--total-limit", type=int, default=500,
        help="전체 최대 수집 수 (기본: 500)",
    )
    parser.add_argument(
        "--limit-per-family", type=int, default=50,
        help="과당 최대 수집 수 (기본: 50)",
    )
    parser.add_argument(
        "--max-per-genus", type=int, default=3,
        help="속(genus)당 최대 수집 수 — 다양성 확보 (기본: 3)",
    )
    parser.add_argument(
        "--images-only", action="store_true",
        help="이미지 있는 식물만 수집",
    )
    parser.add_argument(
        "--resume", nargs="?", const="auto", default=None,
        help="체크포인트에서 이어서 수집. 경로 지정 또는 생략 시 최신 자동 탐색",
    )
    parser.add_argument(
        "--append", action="store_true",
        help="기존 v2_data_patched.json에 새 식물만 추가 (중복 학명 스킵)",
    )
    parser.add_argument(
        "--trim-genus", type=int, default=0,
        help="기존 데이터에서 속당 N건 초과 삭제 후 저장 (e.g. --trim-genus 5)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.strategy == "family" and not args.family:
        print("Error: --family is required for 'family' strategy")
        sys.exit(1)
    if args.strategy == "query" and not args.query:
        print("Error: --query is required for 'query' strategy")
        sys.exit(1)

    etl = FloripediaETL(args=args)
    result = etl.run()
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))