import json
import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from collections import Counter

st.set_page_config(page_title="Floripedia 데이터 점검", layout="wide")

FLAGGED_FILE = os.path.join(os.path.dirname(__file__), "flagged_plants.json")

@st.cache_data
def load_data():
    with open("all_plants.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_flagged():
    if os.path.exists(FLAGGED_FILE):
        with open(FLAGGED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_flagged(flagged):
    with open(FLAGGED_FILE, "w", encoding="utf-8") as f:
        json.dump(flagged, f, ensure_ascii=False, indent=2)

data = load_data()
total = len(data)

# ======== 사이드바: 페이지 선택 ========
st.sidebar.title("Floripedia 점검")
st.sidebar.caption(f"총 {total}건")
page = st.sidebar.radio("페이지", ["Overview", "누락 필드", "전체 보기", "개별 조회", "스토리 점검", "이미지 점검", "검색"])

TOP_KEYS = ["_id", "name", "scientificName", "isRepresentative", "taxonomy",
            "horticulture", "habitat", "stories", "imageUrl", "season",
            "bloomingMonths", "searchKeywords", "popularity_score",
            "colorInfo", "scentInfo", "flowerInfo", "images"]

# ======== Overview ========
if page == "Overview":
    st.title("Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("총 식물 수", total)
    representative = sum(1 for p in data if p.get("isRepresentative"))
    col2.metric("대표 식물", representative)
    col3.metric("비대표 식물", total - representative)

    st.subheader("시즌 분포")
    seasons = Counter(p.get("season", "없음") for p in data)
    st.bar_chart(pd.Series(seasons).sort_index())

    st.subheader("카테고리 그룹 분포")
    cat_groups = Counter(p.get("horticulture", {}).get("categoryGroup", "없음") for p in data)
    st.bar_chart(pd.Series(cat_groups).sort_values(ascending=False))

    st.subheader("꽃말 그룹 분포")
    flower_groups = Counter(p.get("flowerInfo", {}).get("flowerGroup", "없음") for p in data)
    st.bar_chart(pd.Series(flower_groups).sort_values(ascending=False))

    st.subheader("향기 그룹 분포")
    scent_groups = Counter()
    for p in data:
        for sg in p.get("scentInfo", {}).get("scentGroup", ["없음"]):
            scent_groups[sg] += 1
    st.bar_chart(pd.Series(scent_groups).sort_values(ascending=False))

# ======== 누락 필드 ========
elif page == "누락 필드":
    st.title("누락 필드 점검")

    missing_counts = Counter()
    items_missing = {k: [] for k in TOP_KEYS}
    for plant in data:
        for k in TOP_KEYS:
            if k not in plant or plant[k] is None or plant[k] == "" or plant[k] == []:
                missing_counts[k] += 1
                items_missing[k].append(plant.get("name", plant.get("_id", "?")))

    missing_df = pd.DataFrame([
        {"필드": k, "누락 수": missing_counts.get(k, 0), "비율(%)": round(missing_counts.get(k, 0) / total * 100, 1)}
        for k in TOP_KEYS
    ])
    st.dataframe(missing_df, use_container_width=True, hide_index=True)

    field_pick = st.selectbox("누락된 식물 목록 보기", [k for k in TOP_KEYS if missing_counts.get(k, 0) > 0] or ["(없음)"])
    if field_pick != "(없음)" and field_pick in items_missing:
        st.write(f"**{field_pick}** 누락 식물: {', '.join(items_missing[field_pick][:50])}")
        if len(items_missing[field_pick]) > 50:
            st.caption(f"...외 {len(items_missing[field_pick]) - 50}건")

    st.subheader("중복 _id 점검")
    ids = [p.get("_id") for p in data]
    dup_ids = [item for item, count in Counter(ids).items() if count > 1]
    if dup_ids:
        st.error(f"중복 _id 발견: {dup_ids}")
    else:
        st.success("중복 _id 없음")

    st.subheader("중복 name 점검")
    names = [p.get("name") for p in data]
    dup_names = [item for item, count in Counter(names).items() if count > 1]
    if dup_names:
        st.warning(f"중복 name 발견: {dup_names}")
    else:
        st.success("중복 name 없음")

# ======== 전체 보기 (바둑판 그리드) ========
elif page == "전체 보기":
    st.title("전체 보기")

    # 필터
    f1, f2, f3 = st.columns(3)
    with f1:
        all_seasons = sorted(set(p.get("season", "없음") for p in data))
        season_filter = st.multiselect("시즌", all_seasons, default=[])
    with f2:
        all_cats = sorted(set(p.get("horticulture", {}).get("categoryGroup", "없음") for p in data))
        cat_filter = st.multiselect("카테고리", all_cats, default=[])
    with f3:
        grid_cols = st.slider("열 수", 3, 8, 5)

    flagged = load_flagged()
    flag_only = st.checkbox("🚩 플래그된 것만 보기")

    filtered = data
    if season_filter:
        filtered = [p for p in filtered if p.get("season") in season_filter]
    if cat_filter:
        filtered = [p for p in filtered if p.get("horticulture", {}).get("categoryGroup") in cat_filter]
    if flag_only:
        filtered = [p for p in filtered if str(p.get("_id")) in flagged]

    st.caption(f"{len(filtered)}건 표시")

    # 페이지네이션
    per_page = grid_cols * 6  # 6행분
    total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
    if "grid_page" not in st.session_state:
        st.session_state.grid_page = 0
    st.session_state.grid_page = min(st.session_state.grid_page, total_pages - 1)

    gp1, gp2, gp3 = st.columns([1, 2, 1])
    with gp1:
        if st.button("← 이전 페이지", key="grid_prev") and st.session_state.grid_page > 0:
            st.session_state.grid_page -= 1
            st.rerun()
    with gp2:
        st.markdown(f"<div style='text-align:center'>페이지 {st.session_state.grid_page + 1} / {total_pages}</div>",
                    unsafe_allow_html=True)
    with gp3:
        if st.button("다음 페이지 →", key="grid_next") and st.session_state.grid_page < total_pages - 1:
            st.session_state.grid_page += 1
            st.rerun()

    start = st.session_state.grid_page * per_page
    page_data = filtered[start:start + per_page]

    # 그리드 렌더링
    for row_start in range(0, len(page_data), grid_cols):
        cols = st.columns(grid_cols)
        for ci, col in enumerate(cols):
            di = row_start + ci
            if di >= len(page_data):
                break
            p = page_data[di]
            pid = str(p.get("_id", ""))
            is_flag = pid in flagged
            with col:
                img_url = p.get("imageUrl", "")
                if img_url:
                    st.image(img_url, use_container_width=True)
                flag_mark = "🚩 " if is_flag else ""
                st.markdown(
                    f"<div style='text-align:center;font-weight:bold;font-size:0.9em'>"
                    f"{flag_mark}{p.get('name', '?')}</div>"
                    f"<div style='text-align:center;font-size:0.75em;color:gray'>"
                    f"{p.get('scientificName', '')}<br>"
                    f"{p.get('season', '')} | {p.get('flowerInfo', {}).get('language', '')}</div>",
                    unsafe_allow_html=True,
                )
                # 클릭하면 개별 조회로 이동
                real_idx = data.index(p)
                if st.button("상세", key=f"grid_go_{pid}", use_container_width=True):
                    st.session_state.browse_idx = real_idx
                    st.query_params["page"] = "개별 조회"
                    st.rerun()

# ======== 개별 조회 (독립 페이지 + 키보드 화살표) ========
elif page == "개별 조회":
    if "browse_idx" not in st.session_state:
        st.session_state.browse_idx = 0

    # JS: 화살표 키 감지 → hidden button 클릭
    components.html("""
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.key === 'ArrowLeft') {
            const btn = doc.querySelector('button[data-testid="prev-btn"]')
                || [...doc.querySelectorAll('button')].find(b => b.innerText.includes('←'));
            if (btn) btn.click();
        } else if (e.key === 'ArrowRight') {
            const btn = doc.querySelector('button[data-testid="next-btn"]')
                || [...doc.querySelectorAll('button')].find(b => b.innerText.includes('→'));
            if (btn) btn.click();
        }
    });
    </script>
    """, height=0)

    # number_input의 key와 browse_idx 동기화
    def _sync_jump():
        st.session_state.browse_idx = st.session_state._jump

    def _go_prev():
        st.session_state.browse_idx = max(0, st.session_state.browse_idx - 1)

    def _go_next():
        st.session_state.browse_idx = min(total - 1, st.session_state.browse_idx + 1)

    # 네비게이션 바
    nav1, nav2, nav3, nav4 = st.columns([1, 1, 2, 2])
    with nav1:
        st.button("← 이전 (←)", use_container_width=True, key="prev", on_click=_go_prev)
    with nav2:
        st.button("다음 (→) →", use_container_width=True, key="next", on_click=_go_next)
    with nav3:
        st.number_input("번호 이동", min_value=0, max_value=total - 1,
                        value=st.session_state.browse_idx, key="_jump", on_change=_sync_jump)
    with nav4:
        st.markdown(f"<h2 style='text-align:right;margin:0;padding-top:0.3em'>{st.session_state.browse_idx + 1} / {total}</h2>",
                    unsafe_allow_html=True)

    idx = st.session_state.browse_idx
    plant = data[idx]
    plant_id = str(plant.get("_id", idx))

    # --- 플래그 ---
    flagged = load_flagged()
    is_flagged = plant_id in flagged

    def _on_flag_change():
        f = load_flagged()
        checked = st.session_state[f"flag_{plant_id}"]
        if checked:
            f[plant_id] = st.session_state.get(f"memo_{plant_id}", "")
        elif plant_id in f:
            del f[plant_id]
        save_flagged(f)

    def _on_memo_change():
        f = load_flagged()
        if st.session_state.get(f"flag_{plant_id}"):
            f[plant_id] = st.session_state[f"memo_{plant_id}"]
            save_flagged(f)

    fc1, fc2 = st.columns([1, 4])
    with fc1:
        st.checkbox("🚩 문제 있음", value=is_flagged, key=f"flag_{plant_id}", on_change=_on_flag_change)
    with fc2:
        st.text_input("메모", value=flagged.get(plant_id, ""), key=f"memo_{plant_id}",
                      placeholder="어떤 문제인지 간단히 메모...", label_visibility="collapsed",
                      on_change=_on_memo_change)

    st.divider()

    # ---- 카드형 레이아웃 ----
    # 상단: 이미지 + 기본정보 + 메타
    top1, top2, top3 = st.columns([1.2, 1.5, 1.5])

    with top1:
        if plant.get("imageUrl"):
            st.image(plant["imageUrl"], use_container_width=True)
        else:
            st.warning("이미지 없음")

    with top2:
        name = plant.get("name", "-")
        sci = plant.get("scientificName", "-")
        st.markdown(f"## {name}")
        st.caption(f"_{sci}_")

        taxonomy = plant.get("taxonomy", {})
        st.markdown(f"**과:** {taxonomy.get('family', '-')}  |  **속:** {taxonomy.get('genus', '-')}  |  **종:** {taxonomy.get('species', '-')}")

        hort = plant.get("horticulture", {})
        st.markdown(f"**카테고리:** {hort.get('category', '-')} / {hort.get('categoryGroup', '-')}")

        flower = plant.get("flowerInfo", {})
        st.markdown(f"**꽃말:** {flower.get('language', '-')}  ({flower.get('flowerGroup', '-')})")

    with top3:
        m1, m2, m3 = st.columns(3)
        m1.metric("시즌", plant.get("season", "-"))
        m2.metric("인기", plant.get("popularity_score", "-"))
        m3.metric("대표", "O" if plant.get("isRepresentative") else "X")

        months = plant.get("bloomingMonths", [])
        st.markdown(f"**개화월:** {', '.join(str(m) + '월' for m in months) if months else '-'}")

        color = plant.get("colorInfo", {})
        hex_codes = color.get("hexCodes", [])
        color_labels = color.get("colorLabels", [])
        if hex_codes:
            swatches = "".join(f'<span style="display:inline-block;width:20px;height:20px;background:{h};border-radius:4px;margin-right:4px;vertical-align:middle"></span>' for h in hex_codes)
            st.markdown(f"**색상:** {swatches} {', '.join(color_labels)}", unsafe_allow_html=True)

        scent = plant.get("scentInfo", {})
        st.markdown(f"**향기:** {', '.join(scent.get('scentTags', []))}  ({', '.join(scent.get('scentGroup', []))})")

        kws = plant.get("searchKeywords", [])
        if kws:
            badges = " ".join(f"`{k}`" for k in kws)
            st.markdown(f"**키워드:** {badges}")

    # ---- 원예정보 ----
    hort = plant.get("horticulture", {})
    if any(hort.get(k) for k in ["usage", "preContent", "management"]):
        st.divider()
        h1, h2 = st.columns(2)
        with h1:
            if hort.get("preContent"):
                st.markdown("**개요**")
                st.write(hort["preContent"])
            if hort.get("usage"):
                st.markdown("**용도**")
                st.write(" ".join(hort["usage"]))
        with h2:
            if hort.get("management"):
                st.markdown("**관리**")
                st.write(hort["management"])
            if plant.get("habitat"):
                st.markdown("**서식지**")
                st.write(plant["habitat"])

    # ---- 스토리 (항상 표시, 카드형) ----
    stories = plant.get("stories", [])
    if stories:
        st.divider()
        st.markdown("### 스토리")
        genre_style = {
            "MYTH": ("🟣", "#9b59b6"), "HISTORY": ("🟤", "#8B4513"),
            "ART": ("🔵", "#3498db"), "SCIENCE": ("🟢", "#27ae60"),
            "EPISODE": ("🟡", "#f39c12"),
        }
        cols = st.columns(min(len(stories), 2))
        for i, s in enumerate(stories):
            genre = s.get("genre", "?")
            icon, color = genre_style.get(genre, ("⚪", "#888"))
            with cols[i % len(cols)]:
                st.markdown(
                    f'<div style="border-left:4px solid {color};padding:8px 12px;margin-bottom:12px;'
                    f'background:rgba(0,0,0,0.02);border-radius:0 8px 8px 0">'
                    f'<strong>{icon} {genre}</strong><br><span style="font-size:0.95em">{s.get("content", "")}</span></div>',
                    unsafe_allow_html=True,
                )

    # ---- 추가 이미지 ----
    images = plant.get("images", [])
    if images and len(images) > 1:
        st.divider()
        st.markdown(f"### 이미지 ({len(images)}장)")
        img_cols = st.columns(min(len(images), 4))
        for i, img_url in enumerate(images):
            with img_cols[i % len(img_cols)]:
                st.image(img_url, use_container_width=True)

    # ---- JSON ----
    with st.expander("전체 JSON"):
        st.json(plant)

    # ---- 플래그 목록 (사이드바) ----
    flagged = load_flagged()
    if flagged:
        st.sidebar.divider()
        st.sidebar.subheader(f"🚩 플래그 ({len(flagged)}건)")
        for fid, memo in flagged.items():
            match = next((p for p in data if str(p.get("_id")) == fid), None)
            name = match.get("name", "?") if match else "?"
            st.sidebar.markdown(f"- **{fid}** {name}: {memo}")

# ======== 스토리 점검 ========
elif page == "스토리 점검":
    st.title("스토리 점검")
    genre_counter = Counter()
    no_story = []
    story_counts = []
    for p in data:
        stories = p.get("stories", [])
        story_counts.append(len(stories))
        if not stories:
            no_story.append(p.get("name", "?"))
        for s in stories:
            genre_counter[s.get("genre", "없음")] += 1

    st.bar_chart(pd.Series(genre_counter).sort_values(ascending=False))

    col1, col2 = st.columns(2)
    col1.metric("스토리 없는 식물", len(no_story))
    col2.metric("평균 스토리 수", round(sum(story_counts) / max(len(story_counts), 1), 1))

    if no_story:
        st.write("스토리 없는 식물:", ", ".join(no_story[:30]))

    st.subheader("짧은 스토리 (50자 미만)")
    short_stories = []
    for p in data:
        for s in p.get("stories", []):
            content = s.get("content", "")
            if len(content) < 50:
                short_stories.append({"식물": p.get("name"), "장르": s.get("genre"), "길이": len(content), "내용": content})
    if short_stories:
        st.dataframe(pd.DataFrame(short_stories), use_container_width=True, hide_index=True)
    else:
        st.success("50자 미만 스토리 없음")

# ======== 이미지 점검 ========
elif page == "이미지 점검":
    st.title("이미지 점검")
    no_image = []
    img_counts = []
    for p in data:
        imgs = p.get("images", [])
        img_counts.append(len(imgs))
        if not imgs and not p.get("imageUrl"):
            no_image.append(p.get("name", "?"))

    col1, col2 = st.columns(2)
    col1.metric("이미지 없는 식물", len(no_image))
    col2.metric("평균 이미지 수", round(sum(img_counts) / max(len(img_counts), 1), 1))

    st.subheader("이미지 수 분포")
    img_dist = Counter(img_counts)
    st.bar_chart(pd.Series(img_dist).sort_index())

    if no_image:
        st.write("이미지 없는 식물:", ", ".join(no_image[:30]))

# ======== 검색 ========
elif page == "검색":
    st.title("검색")
    query = st.text_input("식물 이름 / 학명 / 키워드 검색")
    if query:
        results = []
        q = query.lower()
        for p in data:
            name = (p.get("name") or "").lower()
            sci = (p.get("scientificName") or "").lower()
            kws = " ".join(p.get("searchKeywords", [])).lower()
            if q in name or q in sci or q in kws:
                results.append({
                    "ID": p.get("_id"),
                    "이름": p.get("name"),
                    "학명": p.get("scientificName"),
                    "시즌": p.get("season"),
                    "카테고리": p.get("horticulture", {}).get("categoryGroup"),
                    "꽃말": p.get("flowerInfo", {}).get("language"),
                    "인기점수": p.get("popularity_score"),
                })
        st.write(f"검색 결과: {len(results)}건")
        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
