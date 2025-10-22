import streamlit as st
import pandas as pd
import os
import requests
from datetime import datetime

# Page config must be set before any Streamlit UI calls
st.set_page_config(page_title="여행·지역·세대별 관광지 추천", layout="wide")

# Load custom styles (styles.css should be in the same folder as app.py)
def local_css(file_name: str):
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        # If styles not found, continue with default Streamlit styles
        st.warning("스타일 파일(styles.css)을 찾을 수 없어 기본 스타일로 표시됩니다.")

local_css('styles.css')

# Header (simple and non-duplicating)
st.markdown("""
<div class="block-container">
    <h1>여행·지역·세대별 관광지 추천</h1>
    <p class="muted">나이, 지역, 계절과 간단한 키워드만 입력하면 바로 추천을 받아볼 수 있어요.</p>
</div>
""", unsafe_allow_html=True)

# 1. 사용자 입력 (사이드바)
with st.sidebar:
    st.header("검색 조건")
    name = st.text_input("이름 (선택)")
    age = st.slider("연령", 10, 80, 30)

    region_full = st.selectbox("여행 희망 지역", [
        "서울특별시", "부산광역시", "제주특별자치도", "강원특별자치도", "대전광역시", "대구광역시"
    ])

    seasons = ["봄", "여름", "가을", "겨울"]
    current_month = datetime.now().month

    def get_current_season(month):
        if 3 <= month <= 5:
            return "봄"
        if 6 <= month <= 8:
            return "여름"
        if 9 <= month <= 11:
            return "가을"
        return "겨울"

    default_season = get_current_season(current_month)
    season = st.selectbox("선호 계절", seasons, index=seasons.index(default_season))

    keyword = st.text_input("검색 키워드 (예: 벚꽃, 해수욕장)")

    # 간단한 추천 키워드 제안 (일반 사용자용)
    season_keywords = {
        "봄": ["벚꽃", "봄꽃축제", "야외공원", "계곡"],
        "여름": ["해수욕장", "계곡", "물놀이", "산책로"],
        "가을": ["단풍", "가을축제", "산책", "호수"],
        "겨울": ["눈꽃", "스키장", "온천", "겨울축제"]
    }
    suggested = st.selectbox("추천 키워드 (선택)", ["(선택)"] + season_keywords.get(default_season, []))
    if suggested and suggested != "(선택)":
        keyword = suggested
    # 관광지 전용 필터 토글 (기본: 해제 -> 키워드 검색 우선)
    filter_only_tourist = st.checkbox("관광지만 보기(정확도↑, 일부 키워드 누락 가능)", value=False)

# 2. 나이 → 세대 텍스트 변환
def get_age_group(age):
    if age < 20:
        return "10대"
    elif 20 <= age < 30:
        return "20대"
    elif 30 <= age < 40:
        return "30대"
    elif 40 <= age < 50:
        return "40대"
    elif 50 <= age < 60:
        return "50대"
    else:
        return "60대"

age_group = get_age_group(age)

# 3. CSV 폴더 경로 설정 (ZIP → 폴더로 변경)
folder_paths = {
    "서울특별시": r"C:\Users\406\Documents\GitHub\-\data\20251021122427_서울특별시_202410-202509_데이터랩_다운로드",
    "부산광역시": r"C:\Users\406\Documents\GitHub\-\data\20251021125950_부산광역시_202410-202509_데이터랩_다운로드",
    "제주특별자치도": r"C:\Users\406\Documents\GitHub\-\data\20251021144848_제주특별자치도_202410-202509_데이터랩_다운로드",
    "강원특별자치도": r"C:\Users\406\Documents\GitHub\-\data\20251021144903_강원특별자치도_202410-202509_데이터랩_다운로드",
    "대전광역시": r"C:\Users\406\Documents\GitHub\-\data\20251021144912_대전광역시_202410-202509_데이터랩_다운로드",
    "대구광역시": r"C:\Users\406\Documents\GitHub\-\data\20251021144926_대구광역시_202410-202509_데이터랩_다운로드"
}

nationwide_folder = r"C:\Users\406\Documents\GitHub\-\data\20251021114705_전국_202410-202509_데이터랩_다운로드"

# 4. 폴더에서 CSV 불러오기
@st.cache_data
def load_csv_from_folder(folder_path, keyword):
    if not os.path.isdir(folder_path):
        st.error(f"경로가 존재하지 않습니다: {folder_path}")
        return None
    for fname in os.listdir(folder_path):
        if keyword in fname and fname.endswith(".csv"):
            try:
                df = pd.read_csv(os.path.join(folder_path, fname), encoding='utf-8')
                return df
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(os.path.join(folder_path, fname), encoding='cp949')
                    return df
                except Exception as e:
                    st.error(f"CSV 파일 인코딩 오류: {e}")
                    return None
    return None

# 5. 데이터 불러오기
df_age = load_csv_from_folder(nationwide_folder, f"세대별 인기관광지({age_group})")
df_region = load_csv_from_folder(folder_paths[region_full], f"세대별 인기관광지({age_group})")

# 6. 병합 및 필수 컬럼만 남기기
if df_age is not None and df_region is not None:
    try:
        df_recommended = pd.merge(df_age, df_region, on='관심지점명', how='inner')
        cols_to_keep = ['순위', '관광지ID', '관심지점명', '연령대', '비율']
        all_cols = df_recommended.columns.tolist()

        selected_cols = []
        for col in cols_to_keep:
            if col in all_cols:
                selected_cols.append(col)
            else:
                for suffix in ['_x', '_y']:
                    if col + suffix in all_cols:
                        selected_cols.append(col + suffix)
                        break

        df_recommended = df_recommended[selected_cols]
        df_recommended.columns = df_recommended.columns.str.strip()
    except Exception as e:
        st.error(f"병합 중 오류 발생: {e}")
        df_recommended = pd.DataFrame()
else:
    st.warning("데이터를 불러오지 못했습니다.")
    df_recommended = pd.DataFrame()

# 7. 실시간 검색(외부 서비스) 키 불러오기
api_key = st.secrets.get("KAKAO_REST_API_KEY", None)

# 카카오 API 관광지만 필터링 함수
def filter_tourist_spots(results, filter_category=True):
    # 카카오 로컬 API에서 관광지 카테고리 그룹코드: 'AT4'
    if not filter_category:
        return results
    return [place for place in results if place.get('category_group_code') == 'AT4']

# 카카오 로컬 API 검색 함수 (통합 및 에러 처리 강화, 키워드 보정 포함)
def search_local_popular(region, keyword, api_key, filter_category=True):
    if not api_key:
        st.warning("API 키가 필요합니다.")
        return []
    if not region:
        st.warning("지역을 입력해 주세요.")
        return []

    # keyword가 비었거나 '관광지'일 때 보정
    if not keyword or keyword.strip() == "" or keyword.strip() == "관광지":
        keyword = "명소"

    query = f"{region} {keyword}"
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    # Kakao Local API allows up to 15 results per request for keyword search
    requested_size = 30
    max_size = 15
    size = min(requested_size, max_size)
    params = {"query": query, "size": size}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
    except requests.RequestException as e:
        st.error(f"네트워크 오류로 카카오 API 호출에 실패했습니다: {e}")
        return []

    # If non-200, show response body where possible to help debugging (400 메시지 등)
    if response.status_code != 200:
        body_text = None
        try:
            body = response.json()
            # Kakao returns a 'message' field in many errors
            body_text = body.get('message') or str(body)
        except Exception:
            body_text = response.text

        st.error(f"카카오 API 호출 실패 (status: {response.status_code})")
        with st.expander("응답 본문 (개발용)"):
            st.write(body_text)

        # Common cause: size too large or malformed query
        if response.status_code == 400:
            st.info("(원인 추정) 요청 파라미터에 문제가 있을 수 있습니다. 쿼리 길이/특수문자 또는 size 파라미터를 확인하세요. 자동으로 size를 15로 제한했습니다.")

        return []

    try:
        data = response.json()
    except Exception as e:
        st.error(f"카카오 응답을 파싱하지 못했습니다: {e}")
        return []

    places = data.get("documents", [])
    return filter_tourist_spots(places, filter_category=filter_category)


def search_places_by_names(names, region, api_key, max_per=1):
    """각 관광지명을 가지고 개별 검색을 수행합니다. 필터는 기본적으로 해제하여 이름 기반 매칭을 우선시합니다."""
    matches = []
    for name in names:
        if not name or pd.isna(name):
            continue
        # sanitize name: remove problematic characters and trim
        qname = str(name).strip()
        qname = qname.replace('\n', ' ').replace('\r', ' ')
        # remove excessive punctuation that may break query
        for ch in ['/', '\\', '?', '&', '%', '#']:
            qname = qname.replace(ch, ' ')
        qname = ' '.join(qname.split())
        res = search_local_popular(region, qname, api_key, filter_category=False)
        if res:
            for r in res[:max_per]:
                matches.append({
                    '원래명': name,
                    '매칭명': r.get('place_name'),
                    '카테고리': r.get('category_name'),
                    '주소': r.get('address_name'),
                    '전화': r.get('phone'),
                    '링크': r.get('place_url')
                })
        else:
            matches.append({'원래명': name, '매칭명': None, '카테고리': None, '주소': None, '전화': None, '링크': None})
    return pd.DataFrame(matches)

# 버튼 클릭 시
if st.button("현지 인기명소 찾아보기"):
    # 빈 키워드인 경우에도 '명소' 키워드로 자동 대체
    search_keyword = keyword
    if not search_keyword or search_keyword.strip() == "":
        search_keyword = "명소"
    elif search_keyword.strip() == "관광지":
        search_keyword = "명소"

    with st.spinner('현지 관광지를 불러오는 중입니다...'):
        kakao_results = search_local_popular(region_full, search_keyword, api_key, filter_category=filter_only_tourist)

    # 필터가 켜져있고 결과가 없으면 자동으로 필터 해제하고 재검색
    if filter_only_tourist and not kakao_results:
        st.info('관광지 전용 필터로는 결과가 없어서 전체 검색으로 재시도합니다...')
        with st.spinner('전체 검색 중...'):
            kakao_results = search_local_popular(region_full, search_keyword, api_key, filter_category=False)

    if kakao_results:
        df_kakao = pd.DataFrame(kakao_results)
        st.subheader(f"현지 관광지 추천 결과 ({len(df_kakao)}건)")
        cols = [c for c in ['place_name', 'category_name', 'address_name', 'phone', 'place_url'] if c in df_kakao.columns]
        display = df_kakao[cols].fillna("-")
        display = display.rename(columns={
            'place_name': '장소명',
            'category_name': '카테고리',
            'address_name': '주소',
            'phone': '전화번호',
            'place_url': '상세보기 링크'
        })
        st.markdown('<div class="recommend-card">', unsafe_allow_html=True)
        st.dataframe(display)
        st.markdown('</div>', unsafe_allow_html=True)
        st.success("더 많은 결과는 상세보기 링크에서 확인하세요.")
    else:
        st.warning("검색 결과가 없습니다. 키워드를 바꿔 시도해 보세요.")
