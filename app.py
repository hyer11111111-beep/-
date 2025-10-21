import streamlit as st
import pandas as pd
import zipfile
import os
import requests
from datetime import datetime

st.title("맞춤형 관광지 추천 — 연령 · 지역 · 계절 · 키워드 기반")

st.markdown("""
본 서비스는 사용자의 연령대, 희망 지역, 선호 계절 및 키워드를 바탕으로 신뢰할 수 있는 데이터 소스를 결합해 맞춤형 관광지를 추천합니다.
간결하고 직관적인 인터페이스로 추천 결과를 제공합니다.
""")

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

# 3. ZIP 파일 경로 설정 (예시)
zip_paths = {
    "서울특별시": r"C:\Users\406\Downloads\20251021122427_서울특별시_202410-202509_데이터랩_다운로드.zip",
    "부산광역시": r"C:\Users\406\Downloads\20251021125950_부산광역시_202410-202509_데이터랩_다운로드.zip",
    "제주특별자치도": r"C:\Users\406\Downloads\20251021144848_제주특별자치도_202410-202509_데이터랩_다운로드.zip",
    "강원특별자치도": r"C:\Users\406\Downloads\20251021144903_강원특별자치도_202410-202509_데이터랩_다운로드.zip",
    "대전광역시": r"C:\Users\406\Downloads\20251021144912_대전광역시_202410-202509_데이터랩_다운로드.zip",
    "대구광역시": r"C:\Users\406\Downloads\20251021144926_대구광역시_202410-202509_데이터랩_다운로드.zip"
}

nationwide_zip = r"C:\Users\406\Downloads\20251021114705_전국_202410-202509_데이터랩_다운로드.zip"

# 4. ZIP 안 CSV 읽기 함수
@st.cache_data
def load_csv_from_zip(zip_path, keyword):
    extract_to = "unzipped"
    os.makedirs(extract_to, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    for fname in os.listdir(extract_to):
        if keyword in fname and fname.endswith(".csv"):
            df = pd.read_csv(os.path.join(extract_to, fname), encoding='utf-8')
            return df
    return None

# 5. 데이터 불러오기
df_age = load_csv_from_zip(nationwide_zip, f"세대별 인기관광지({age_group})")
df_region = load_csv_from_zip(zip_paths[region_full], f"세대별 인기관광지({age_group})")

# 6. (선택) 컬럼 확인은 개발/디버깅 시에만 사용합니다. 운영 시 주석 처리 권장.

# 7. 병합 및 필수 컬럼만 남기기
if df_age is not None and df_region is not None:
    try:
        df_recommended = pd.merge(df_age, df_region, on='관심지점명', how='inner')

        # '순위', '관광지ID', '관심지점명', '연령대', '비율' 컬럼만 남기기
        cols_to_keep = ['순위', '관광지ID', '관심지점명', '연령대', '비율']

        # 만약 병합하면서 컬럼명 충돌로 _x, _y 붙었다면 처리
        all_cols = df_recommended.columns.tolist()

        # 실제로 남은 컬럼 중 위 컬럼들 이름 포함한 거 찾기
        selected_cols = []
        for col in cols_to_keep:
            if col in all_cols:
                selected_cols.append(col)
            else:
                # _x 또는 _y 붙은 컬럼 찾기
                for suffix in ['_x', '_y']:
                    if col + suffix in all_cols:
                        selected_cols.append(col + suffix)
                        break

        df_recommended = df_recommended[selected_cols]
        # 컬럼명 앞뒤 공백 제거
        df_recommended.columns = df_recommended.columns.str.strip()
    except Exception as e:
        st.error(f"병합 중 오류 발생: {e}")
        df_recommended = pd.DataFrame()
else:
    st.warning("데이터를 불러오지 못했습니다.")
    df_recommended = pd.DataFrame()

# 8. 카카오 API 키 숨겨서 불러오기
api_key = st.secrets["KAKAO_REST_API_KEY"]

# 9. 카카오 API 함수 (키워드, 지역 기반 검색)
def search_kakao_local(region, keyword, api_key):
    # 기본 입력 검증
    if not api_key:
        st.error("카카오 REST API 키가 설정되어 있지 않습니다. `st.secrets` 또는 secrets.toml을 확인하세요.")
        return []
    if not region or not keyword:
        st.warning("지역과 키워드를 모두 입력해야 검색할 수 있습니다.")
        return []

    query = f"{region} {keyword}"
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {"query": query, "size": 20}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
    except requests.RequestException as e:
        st.error(f"카카오 API 호출 중 네트워크 오류가 발생했습니다: {e}")
        return []

    # 응답 검사: 실패 시 상세 메시지 표출(디버깅용)
    if response.status_code != 200:
        # 가능한 디버깅 정보를 함께 출력
        try:
            body = response.json()
        except Exception:
            body = response.text
        st.error(f"카카오 API 호출 실패 (status: {response.status_code})")
        with st.expander("응답 상세 (디버깅)"):
            st.write(body)
        return []

    # 정상 응답
    try:
        return response.json().get("documents", [])
    except ValueError:
        st.error("카카오 API 응답을 파싱하지 못했습니다.")
        return []

# 10. 버튼 누르면 카카오 API 호출 및 결과 보여주기
if st.button("카카오 API로 키워드 검색"):
    if not keyword:
        st.warning("검색 키워드를 입력하세요.")
    else:
        kakao_results = search_kakao_local(region_full, keyword, api_key)
        if kakao_results:
            df_kakao = pd.DataFrame(kakao_results)
            st.subheader(f"카카오 API 검색 결과 ({len(df_kakao)}건)")
            # 주로 보여줄 컬럼만 선택
            cols = [c for c in ['place_name', 'address_name', 'phone'] if c in df_kakao.columns]
            st.dataframe(df_kakao[cols].fillna("-"))
        else:
            st.warning("검색 결과가 없습니다. (키, 네트워크, 쿼리 확인) ")

# 11. 최종 추천 결과 보여주기
def drop_sensitive_columns(df: pd.DataFrame) -> pd.DataFrame:
    """'관광지ID' 및 '관광지명' 계열 컬럼을 제거(안전하게)합니다.

    대소문자, 공백, _x/_y 접미사 변형을 모두 처리합니다.
    """
    if df is None or df.empty:
        return df
    cols = df.columns.tolist()
    to_drop = []
    normalized_targets = {"관광지id", "관광지id" , "관광지명", "관광지명"}
    for col in cols:
        norm = col.replace(" ", "").lower()
        # 접미사 제거 (_x, _y)
        if norm.endswith("_x") or norm.endswith("_y"):
            norm = norm[:-2]
        if any(target in norm for target in normalized_targets):
            to_drop.append(col)
    if to_drop:
        df = df.drop(columns=to_drop, errors='ignore')
    return df

if not df_recommended.empty:
    # 카카오 인기 관광지 표시용 (관심지점명 기준)
    if 'kakao_results' in locals() and kakao_results:
        kakao_names = [place['place_name'] for place in kakao_results]
        df_recommended['카카오인기지'] = df_recommended['관심지점명'].apply(lambda x: "예" if x in kakao_names else "아니오")
    else:
        df_recommended['카카오인기지'] = "검색없음"
    
    # 카카오 인기 여부 컬럼 추가
    if 'kakao_results' in locals() and kakao_results:
        kakao_names = [place['place_name'] for place in kakao_results]
        if '관심지점명' in df_recommended.columns:
            df_recommended['카카오인기지'] = df_recommended['관심지점명'].apply(lambda x: "예" if x in kakao_names else "아니오")
        else:
            df_recommended['카카오인기지'] = "검색없음"
    else:
        df_recommended['카카오인기지'] = "검색없음"

    # 민감/불필요 컬럼 제거
    df_display = drop_sensitive_columns(df_recommended.copy())

    # 제목 및 출력
    header_name = f"{name}님, 추천 관광지 리스트" if name else "추천 관광지 리스트"
    st.header(header_name)
    st.subheader(f"대상: {age_group} | 지역: {region_full} | 계절: {season}")
    st.dataframe(df_display)
else:
    st.info("추천 데이터가 없습니다.")

st.markdown("""
---
데이터 출처: 데이터랩 관광지 빅데이터 (https://datalab.visitkorea.or.kr/)
""")
