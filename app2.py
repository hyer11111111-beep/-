import streamlit as st
import pandas as pd
import zipfile
import os
import requests
from datetime import datetime

# 1️⃣ 사용자 입력
st.title("📌 나이대 + 지역별 + 계절별 맞춤 관광지 추천")

name = st.text_input("이름")
age = st.slider("나이", 10, 80, 30)

region_full = st.selectbox("여행 희망 지역", [
    "서울특별시", "부산광역시", "제주특별자치도", "강원특별자치도", "대전광역시", "대구광역시"
])

# 계절 선택 (자동 계산 or 수동 선택)
seasons = ["봄", "여름", "가을", "겨울"]
current_month = datetime.now().month

def get_current_season(month):
    if 3 <= month <= 5:
        return "봄"
    elif 6 <= month <= 8:
        return "여름"
    elif 9 <= month <= 11:
        return "가을"
    else:
        return "겨울"

default_season = get_current_season(current_month)
season = st.selectbox("선호 계절 선택", seasons, index=seasons.index(default_season))

# 2️⃣ 나이 → 세대 텍스트
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

# 3️⃣ 지역명 → 짧은 키워드 (파일명용)
region_keywords = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "제주특별자치도": "제주",
    "강원특별자치도": "강원",
    "대전광역시": "대전",
    "대구광역시": "대구"
}

region_short = region_keywords[region_full]

# 4️⃣ ZIP 경로 매핑
zip_paths = {
    "서울특별시": r"C:\Users\406\Downloads\20251021122427_서울특별시_202410-202509_데이터랩_다운로드.zip",
    "부산광역시": r"C:\Users\406\Downloads\20251021125950_부산광역시_202410-202509_데이터랩_다운로드.zip",
    "제주특별자치도": r"C:\Users\406\Downloads\20251021144848_제주특별자치도_202410-202509_데이터랩_다운로드.zip",
    "강원특별자치도": r"C:\Users\406\Downloads\20251021144903_강원특별자치도_202410-202509_데이터랩_다운로드.zip",
    "대전광역시": r"C:\Users\406\Downloads\20251021144912_대전광역시_202410-202509_데이터랩_다운로드.zip",
    "대구광역시": r"C:\Users\406\Downloads\20251021144926_대구광역시_202410-202509_데이터랩_다운로드.zip"
}

nationwide_zip = r"C:\Users\406\Downloads\20251021114705_전국_202410-202509_데이터랩_다운로드.zip"

# 5️⃣ ZIP 내 CSV 로딩 함수
@st.cache_data
def load_csv_from_zip(zip_path, keyword):
    extract_to = "unzipped"
    os.makedirs(extract_to, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    for fname in os.listdir(extract_to):
        if keyword in fname and fname.endswith(".csv"):
            return pd.read_csv(os.path.join(extract_to, fname), encoding='utf-8')
    return None

# 6️⃣ 데이터 로딩
df_age = load_csv_from_zip(nationwide_zip, f"세대별 인기관광지({age_group})")
df_region = load_csv_from_zip(zip_paths[region_full], f"세대별 인기관광지({age_group})")  # 지역별도 세대별 파일임

# 7️⃣ 추천 관광지 도출 (세대 + 지역 기반)
if df_age is not None and df_region is not None:
    try:
        # '관심지점명' → '관광지명'으로 통일
        df_age.rename(columns={'관심지점명': '관광지명'}, inplace=True)
        df_region.rename(columns={'관심지점명': '관광지명'}, inplace=True)

        df_recommended = pd.merge(df_age, df_region, on='관광지명')
    except KeyError:
        st.error("데이터에 '관심지점명' 또는 '관광지명' 컬럼이 없습니다. CSV 파일을 확인해주세요.")
        df_recommended = pd.DataFrame()
else:
    st.warning("데이터를 불러오지 못했습니다. ZIP 경로 및 파일명을 확인하세요.")
    df_recommended = pd.DataFrame()

# 8️⃣ 카카오 API를 이용한 계절별 인기 키워드 기반 관광지 검색 함수
def search_kakao_local(query, api_key):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {"query": query, "size": 10}
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        return res.json()['documents']
    else:
        st.error(f"카카오 API 호출 실패 (status: {res.status_code})")
        return []

# 9️⃣ 계절별 키워드 (예시)
season_keywords = {
    "봄": ["벚꽃", "봄꽃축제", "야외공원", "계곡"],
    "여름": ["해수욕장", "계곡", "물놀이", "산책로"],
    "가을": ["단풍", "가을축제", "산책", "호수"],
    "겨울": ["눈꽃", "스키장", "온천", "겨울축제"]
}

# 🔟 카카오 API 키
api_key = st.secrets["KAKAO_REST_API_KEY"]

# 1️⃣1️⃣ 계절별 인기 키워드로 관광지 검색
all_kakao_places = []
for keyword in season_keywords[season]:
    results = search_kakao_local(f"{region_full} {keyword}", api_key)
    all_kakao_places.extend(results)

# 중복 제거 및 데이터프레임 변환
unique_places = {p['id']: p for p in all_kakao_places}
df_kakao = pd.DataFrame(unique_places.values())

# 1️⃣2️⃣ 최종 추천 리스트에 카카오 API 관광지명 포함 여부 표시
if not df_recommended.empty and not df_kakao.empty:
    df_recommended['카카오인기지'] = df_recommended['관광지명'].apply(
        lambda x: "예" if any(x in name for name in df_kakao['place_name']) else "아니오"
    )
else:
    df_recommended['카카오인기지'] = "데이터없음"

# 1️⃣3️⃣ 결과 출력
st.header(f"안녕하세요, {name}님! {age_group} 세대와 {region_full} 지역, {season} 추천 관광지입니다.")
st.table(df_recommended[['관광지명', '카카오인기지']])



