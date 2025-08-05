import streamlit as st
import os
import tempfile
from image_analyzer import ImageAnalyzer
from template_generator import AdvancedTemplateGenerator
import pandas as pd
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="나만의 블로그 생성기",
    page_icon="📝",
    layout="wide"
)

def check_api_key():
    """API 키 확인"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        st.error("❌ GEMINI_API_KEY가 .env 파일에 설정되지 않았습니다!")
        st.info("💡 .env 파일을 생성하고 GEMINI_API_KEY=your_api_key 를 추가해주세요.")
        return False
    return True

def get_style_analyzer():
    """StyleAnalyzer 지연 로딩"""
    try:
        from style_analyzer import StyleAnalyzer
        api_key = os.getenv('GEMINI_API_KEY')
        return StyleAnalyzer(api_key)
    except Exception as e:
        st.error(f"StyleAnalyzer 로딩 실패: {e}")
        st.info("💡 스타일 학습 기능을 사용하려면 style_analyzer.py 파일을 확인해주세요.")
        return None

def main():
    st.title("📝 나만의 블로그 생성기")
    st.markdown("### 🤖 AI로 1000자 이상의 상세한 여행 블로그를 자동 생성해보세요!")
    
    # API 키 확인
    if not check_api_key():
        return
    
    # 사이드바
    st.sidebar.header("🎯 설정")
    st.sidebar.success("✅ Gemini API 연결됨")
    
    # 블로그 생성 모드 선택
    st.sidebar.subheader("🤖 블로그 생성 모드")
    
    # 스타일 학습 기능 사용 가능 여부 확인
    style_analyzer_available = True
    try:
        from style_analyzer import StyleAnalyzer
    except ImportError:
        style_analyzer_available = False
    
    if style_analyzer_available:
        blog_mode_options = ['enhanced_basic', 'style_learning']
        blog_mode_labels = {
            'enhanced_basic': '🚀 AI 강화 템플릿 (1000자+)',
            'style_learning': '🧠 스타일 학습 (고급)'
        }
    else:
        blog_mode_options = ['enhanced_basic']
        blog_mode_labels = {
            'enhanced_basic': '🚀 AI 강화 템플릿 (1000자+)'
        }
        st.sidebar.warning("⚠️ 스타일 학습 기능을 사용할 수 없습니다.")
    
    blog_mode = st.sidebar.radio(
        "어떤 방식으로 블로그를 생성할까요?",
        options=blog_mode_options,
        format_func=lambda x: blog_mode_labels[x]
    )
    
    # 스타일 학습 모드일 때만 표시
    reference_blog_data = None
    if blog_mode == 'style_learning' and style_analyzer_available:
        st.sidebar.markdown("---")
        st.sidebar.subheader("📚 참고 블로그")
    
        # 입력 방식 선택
        input_method = st.sidebar.radio(
            "참고 블로그 입력 방식",
            ['url_gemini', 'manual'],
            format_func=lambda x: {
                'url_gemini': '🌐 URL (Gemini 직접 분석)',
                'manual': '✋ 직접 입력'
            }[x]
        )
    
        if input_method == 'url_gemini':
            with st.sidebar.expander("🌐 블로그 URL 입력", expanded=True):
                ref_url = st.text_input(
                    "블로그 URL",
                    placeholder="https://blog.naver.com/...",
                    help="Gemini가 직접 해당 페이지에 접속해서 스타일을 분석합니다."
                )
            
                if ref_url:
                    if ref_url.startswith(('http://', 'https://')):
                        reference_blog_data = {
                            'url': ref_url,
                            'method': 'url_gemini'
                        }
                        st.sidebar.success("✅ URL이 설정되었습니다!")
                    else:
                        st.sidebar.error("❌ 올바른 URL을 입력해주세요 (http:// 또는 https://)")
    
        else:  # manual
            with st.sidebar.expander("📝 참고 블로그 내용 입력", expanded=True):
                ref_title = st.text_input("참고 블로그 제목")
                ref_content = st.text_area(
                    "참고 블로그 본문", 
                    height=200,
                    placeholder="참고하고 싶은 블로그의 제목과 본문을 복사해서 붙여넣기 하세요..."
                )
            
                if ref_title and ref_content:
                    reference_blog_data = {
                        'title': ref_title,
                        'content': ref_content,
                        'method': 'manual'
                    }
    
    # 메인 영역
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 이미지 업로드
        uploaded_files = st.file_uploader(
            "📸 이미지를 업로드하세요 (최대 5장)",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            help="여행 사진들을 업로드하면 GPS 정보와 텍스트를 자동으로 분석합니다."
        )
        
        # 키워드 입력
        keywords = st.text_input(
            "🔍 블로그 주제 키워드를 입력하세요",
            placeholder="예: 부산 여행, 당일치기 서울 근교, 맛집 투어, 데이트 코스"
        )
        
        # 템플릿 선택 (강화된 기본 모드일 때만)
        template_type = 'auto'
        if blog_mode == 'enhanced_basic':
            st.subheader("📄 블로그 스타일 선택")
            template_type = st.selectbox(
                "어떤 스타일의 블로그를 만들까요?",
                options=['auto', 'daytour', 'food', 'date'],
                format_func=lambda x: {
                    'auto': '🤖 자동 선택 (키워드 기반)',
                    'daytour': '🚗 당일치기 여행',
                    'food': '🍴 맛집 투어',
                    'date': '💕 데이트 코스'
                }[x]
            )
    
    with col2:
        # 기능 소개
        st.markdown("### 🌟 새로운 기능")
        if style_analyzer_available:
            st.info("""
            **🚀 AI 강화 템플릿**
            - 1000자 이상 상세 블로그
            - 실용적인 정보 자동 추가
            - 생생한 경험담 생성
            
            **🧠 스타일 학습**
            - 참고 블로그 문체 모방
            - 개성있는 표현 학습
            - 맞춤형 블로그 생성
            """)
        else:
            st.info("""
            **🚀 AI 강화 템플릿**
            - 1000자 이상 상세 블로그
            - 실용적인 정보 자동 추가
            - 생생한 경험담 생성
            
            💡 스타일 학습 기능은 style_analyzer.py 파일을 설정하면 사용할 수 있습니다.
            """)
        
        if uploaded_files:
            st.markdown("### 📊 업로드 현황")
            st.success(f"✅ {len(uploaded_files)}장 업로드됨")
            
            if len(uploaded_files) > 5:
                st.error("❌ 최대 5장까지 가능")
            else:
                # 이미지 미리보기
                for i, file in enumerate(uploaded_files[:3]):
                    st.image(file, caption=f"이미지 {i+1}", width=150)
                
                if len(uploaded_files) > 3:
                    st.write(f"+ {len(uploaded_files)-3}장 더...")
    
    # 생성 버튼 및 조건 확인
    if uploaded_files and len(uploaded_files) <= 5 and keywords:
        if blog_mode == 'enhanced_basic' or (blog_mode == 'style_learning' and reference_blog_data):
            
            # 예상 생성 정보
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📸 분석할 이미지", f"{len(uploaded_files)}장")
            with col2:
                st.metric("📝 예상 글자 수", "1000자 이상")
            with col3:
                generation_time = "2-3분" if blog_mode == 'enhanced_basic' else "3-5분"
                st.metric("⏱️ 예상 소요시간", generation_time)
            
            # 생성 시작 버튼
            button_text = "🚀 AI 강화 블로그 생성 시작!" if blog_mode == 'enhanced_basic' else "🧠 스타일 학습 블로그 생성 시작!"
            
            if st.button(button_text, type="primary", use_container_width=True):
                if blog_mode == 'enhanced_basic':
                    generate_enhanced_blog(uploaded_files, keywords, template_type)
                else:
                    generate_style_learned_blog(uploaded_files, keywords, reference_blog_data)
        
        else:
            if blog_mode == 'style_learning' and not reference_blog_data:
                st.warning("⚠️ 참고 블로그를 입력해주세요!")
    
    elif uploaded_files and len(uploaded_files) > 5:
        st.error("❌ 최대 5장까지만 업로드 가능합니다!")
    elif not uploaded_files or not keywords:
        st.info("💡 이미지와 키워드를 입력하면 AI가 상세한 블로그를 생성해드려요!")

def generate_enhanced_blog(uploaded_files, keywords, template_type):
    """AI 강화 블로그 생성"""
    
    # 진행상황 표시
    progress_container = st.container()
    with progress_container:
        st.markdown("### 🤖 AI 블로그 생성 중...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 단계별 진행 표시
        steps = [
            "🔧 AI 시스템 초기화",
            "📸 이미지 분석",
            "🧠 AI 정보 수집",
            "✍️ 상세 블로그 생성",
            "🎨 최종 완성"
        ]
        
        current_step = 0
        status_text.text(f"Step {current_step + 1}/5: {steps[current_step]}")
    
    try:
        # 분석기 초기화
        if 'analyzer' not in st.session_state:
            st.session_state.analyzer = ImageAnalyzer()
            progress_bar.progress(0.1)
        
        if 'enhanced_generator' not in st.session_state:
            st.session_state.enhanced_generator = AdvancedTemplateGenerator()
            progress_bar.progress(0.2)
            current_step = 1
            status_text.text(f"Step {current_step + 1}/5: {steps[current_step]}")
        
        analyzer = st.session_state.analyzer
        generator = st.session_state.enhanced_generator
        analysis_results = []
        
        # 이미지 분석
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Step 2/5: 📸 이미지 {i+1}/{len(uploaded_files)} 분석 중...")
            progress_bar.progress(0.2 + (i + 1) / len(uploaded_files) * 0.3)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            try:
                result = analyzer.analyze_image(tmp_path)
                result['keywords'] = keywords
                analysis_results.append(result)
            except Exception as e:
                st.warning(f"⚠️ 이미지 {i+1} 분석 중 오류: {e}")
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        # 템플릿 자동 선택
        if template_type == 'auto':
            template_type = auto_select_template(keywords)
            st.info(f"🤖 키워드 분석 결과: **{get_template_name(template_type)}** 스타일이 선택되었습니다!")
        
        # AI 강화 블로그 생성
        current_step = 2
        status_text.text(f"Step {current_step + 1}/5: {steps[current_step]}")
        progress_bar.progress(0.5)
        
        current_step = 3
        status_text.text(f"Step {current_step + 1}/5: {steps[current_step]}")
        progress_bar.progress(0.8)
        
        blog_content = generator.generate_enhanced_blog_content(analysis_results, keywords, template_type)
        
        current_step = 4
        status_text.text(f"Step {current_step + 1}/5: {steps[current_step]}")
        progress_bar.progress(1.0)
        
        # 진행 상황 컨테이너 제거
        progress_container.empty()
        
        # 결과 표시
        display_enhanced_blog_results(analysis_results, keywords, template_type, blog_content, generator)
        
    except Exception as e:
        progress_container.empty()
        st.error(f"❌ AI 블로그 생성 실패: {e}")
        st.info("💡 .env 파일의 GEMINI_API_KEY를 확인해주세요.")

def generate_style_learned_blog(uploaded_files, keywords, reference_blog_data):
    """스타일 학습 블로그 생성"""
    
    progress_container = st.container()
    with progress_container:
        st.markdown("### 🧠 스타일 학습 블로그 생성 중...")
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    try:
        # 분석기 초기화
        if 'analyzer' not in st.session_state:
            status_text.text("🤖 이미지 분석기 초기화 중...")
            st.session_state.analyzer = ImageAnalyzer()
            progress_bar.progress(0.1)
        
        if 'style_analyzer' not in st.session_state:
            status_text.text("🧠 스타일 분석기 초기화 중...")
            st.session_state.style_analyzer = get_style_analyzer()
            if st.session_state.style_analyzer is None:
                progress_container.empty()
                st.error("❌ 스타일 분석기를 초기화할 수 없습니다.")
                return
            progress_bar.progress(0.2)
        
        analyzer = st.session_state.analyzer
        style_analyzer = st.session_state.style_analyzer
        
        # 이미지 분석
        analysis_results = []
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"📸 이미지 {i+1}/{len(uploaded_files)} 분석 중...")
            progress_bar.progress(0.2 + (i + 1) / len(uploaded_files) * 0.3)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            try:
                result = analyzer.analyze_image(tmp_path)
                result['keywords'] = keywords
                analysis_results.append(result)
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        # 스타일 분석
        status_text.text("📚 참고 블로그 스타일 분석 중...")
        progress_bar.progress(0.6)

        if reference_blog_data['method'] == 'url_gemini':
            status_text.text("🌐 Gemini가 직접 웹페이지 분석 중...")
            style_result = style_analyzer.analyze_blog_style_hybrid(reference_blog_data['url'])
        else:
            style_result = style_analyzer.analyze_blog_style_manual(
                reference_blog_data['title'],
                reference_blog_data['content']
            )

        if 'error' in style_result:
            progress_container.empty()
            st.error(f"❌ 스타일 분석 실패: {style_result['error']}")
            if 'suggestion' in style_result:
                st.info(f"💡 {style_result['suggestion']}")
            return
        
        # 사용자 정보 정리
        status_text.text("📝 여행 정보 정리 중...")
        progress_bar.progress(0.8)
        
        user_content = prepare_user_content(analysis_results, keywords)
        
        # 스타일 적용 블로그 생성
        status_text.text("🎨 스타일 적용 블로그 생성 중...")
        progress_bar.progress(0.9)
        
        blog_content = style_analyzer.generate_blog_with_style(
            user_content,
            style_result['style_analysis'],
            keywords
        )
        
        progress_bar.progress(1.0)
        status_text.text("✅ 스타일 학습 블로그 생성 완료!")
        
        # 진행 상황 컨테이너 제거
        progress_container.empty()
        
        # 결과 표시
        display_style_learned_results(analysis_results, keywords, style_result, blog_content, user_content)
        
    except Exception as e:
        progress_container.empty()
        st.error(f"❌ 스타일 학습 블로그 생성 실패: {e}")
        st.info("💡 참고 블로그 내용을 확인하거나 API 키를 점검해주세요.")

def display_enhanced_blog_results(analysis_results, keywords, template_type, blog_content, generator):
    """AI 강화 블로그 결과 표시"""
    
    st.markdown("---")
    st.header("🎉 AI 강화 블로그 생성 완료!")
    
    # 성과 지표
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📝 생성된 글자 수", f"{len(blog_content):,}자")
    with col2:
        st.metric("📊 분석된 이미지", f"{len(analysis_results)}장")
    with col3:
        word_count = len(blog_content.split())
        st.metric("🔤 단어 수", f"{word_count:,}개")
    with col4:
        st.metric("🎨 블로그 타입", get_template_name(template_type))
    
    # 탭으로 구분
    tab1, tab2, tab3, tab4 = st.tabs(["📝 완성된 블로그", "💡 제목 추천", "📊 분석 결과", "🎯 생성 과정"])
    
    with tab1:
        st.subheader(f"🚀 AI 강화 {get_template_name(template_type)}")
        
        # 블로그 내용 표시
        with st.container():
            st.markdown("### 📖 블로그 내용")
            st.markdown(blog_content)
        
        # 다운로드 기능
        st.markdown("---")
        st.subheader("💾 다운로드")
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📥 텍스트 파일로 다운로드",
                data=blog_content,
                file_name=f"{keywords}_AI강화블로그_{template_type}.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        with col2:
            st.download_button(
                label="📥 마크다운 파일로 다운로드", 
                data=blog_content,
                file_name=f"{keywords}_AI강화블로그_{template_type}.md",
                mime="text/markdown",
                use_container_width=True
            )
    
    with tab2:
        st.subheader("💡 AI 생성 제목 추천 5개")
        
        for i in range(5):
            title = generator.generate_title(keywords, template_type)
            st.write(f"**{i+1}.** {title}")
        
        st.info("💬 마음에 드는 제목을 선택해서 블로그에 사용하세요!")
    
    with tab3:
        st.subheader("📊 이미지 분석 상세 결과")
        display_detailed_analysis(analysis_results)
    
    with tab4:
        st.subheader("🎯 AI 생성 과정")
        st.markdown("""
        **1단계: 이미지 분석**
        - OCR을 통한 텍스트 추출
        - GPS 정보 분석
        - 메타데이터 수집
        
        **2단계: AI 정보 보강**
        - Gemini AI로 추가 정보 생성
        - 실용적인 팁과 조언 추가
        - 생생한 경험담 생성
        
        **3단계: 상세 블로그 작성**
        - 1000자 이상 상세 내용
        - 네이버 블로그 스타일 적용
        - 개성있는 표현 추가
        """)

def display_detailed_analysis(analysis_results):
    """상세 분석 결과 표시"""
    
    # 요약 통계
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("분석된 이미지", len(analysis_results))
    with col2:
        gps_count = sum(1 for r in analysis_results if r['exif_data'].get('location'))
        st.metric("GPS 정보 있음", gps_count)
    with col3:
        text_count = sum(1 for r in analysis_results if r['extracted_text'])
        st.metric("텍스트 추출됨", text_count)
    
    # 상세 정보
    if st.checkbox("📋 상세 분석 결과 보기"):
        for i, result in enumerate(analysis_results):
            with st.expander(f"📸 이미지 {i+1}: {result['file_name']}", expanded=False):
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📍 위치 정보:**")
                    if result['exif_data'].get('location'):
                        st.success(f"✅ {result['exif_data']['location']}")
                        if result['exif_data'].get('datetime'):
                            st.info(f"📅 촬영: {result['exif_data']['datetime']}")
                    else:
                        st.warning("❌ GPS 정보 없음")
                
                with col2:
                    st.markdown("**📝 추출된 텍스트:**")
                    if result['extracted_text']:
                        for j, text in enumerate(result['extracted_text'][:5]):
                            st.write(f"{j+1}. {text}")
                        if len(result['extracted_text']) > 5:
                            st.write(f"... 외 {len(result['extracted_text']) - 5}개 더")
                    else:
                        st.warning("❌ 추출된 텍스트 없음")

def display_style_learned_results(analysis_results, keywords, style_result, blog_content, user_content):
    """스타일 학습 결과 표시"""
    
    st.markdown("---")
    st.header("🎉 스타일 학습 블로그 생성 완료!")
    
    # 성과 지표
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 생성된 글자 수", f"{len(blog_content):,}자")
    with col2:
        st.metric("📊 분석된 이미지", f"{len(analysis_results)}장")
    with col3:
        word_count = len(blog_content.split())
        st.metric("🔤 단어 수", f"{word_count:,}개")
    
    tab1, tab2, tab3 = st.tabs(["📝 완성된 블로그", "🧠 스타일 분석", "📊 분석 결과"])
    
    with tab1:
        st.subheader("🎨 스타일 학습된 블로그")
        st.markdown(blog_content)
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 텍스트 파일로 다운로드",
                data=blog_content,
                file_name=f"{keywords}_스타일학습_블로그.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col2:
            st.download_button(
                "📥 마크다운 파일로 다운로드",
                data=blog_content,
                file_name=f"{keywords}_스타일학습_블로그.md",
                mime="text/markdown",
                use_container_width=True
            )
    
    with tab2:
        st.subheader("🔍 참고 블로그 스타일 분석")
        st.markdown("**참고 블로그 정보:**")
        st.write(f"- 제목: {style_result['blog_data']['title']}")
        st.write(f"- 내용 길이: {style_result['blog_data']['content_length']}자")
        
        st.markdown("**스타일 분석 결과:**")
        st.markdown(style_result['style_analysis'])
    
    with tab3:
        st.subheader("📊 이미지 분석 결과")
        display_detailed_analysis(analysis_results)

# 보조 함수들
def auto_select_template(keywords):
    keywords_lower = keywords.lower()
    food_keywords = ['맛집', '음식', '먹방', '카페', '레스토랑', '맛', '요리']
    date_keywords = ['데이트', '연인', '커플', '로맨틱', '사랑', '애인']
    
    if any(keyword in keywords_lower for keyword in food_keywords):
        return 'food'
    elif any(keyword in keywords_lower for keyword in date_keywords):
        return 'date'
    else:
        return 'daytour'

def get_template_name(template_type):
    names = {'daytour': '당일치기 여행', 'food': '맛집 투어', 'date': '데이트 코스'}
    return names.get(template_type, '당일치기 여행')

def prepare_user_content(analysis_results, keywords):
    locations = []
    texts = []
    
    for result in analysis_results:
        if result['exif_data'].get('location'):
            locations.append(result['exif_data']['location'])
        if result['extracted_text']:
            texts.extend(result['extracted_text'])
    
    return f"""
키워드: {keywords}
방문 장소: {', '.join(locations) if locations else '정보 없음'}
추출된 텍스트: {', '.join(texts[:10]) if texts else '정보 없음'}
이미지 수: {len(analysis_results)}장
"""

if __name__ == "__main__":
    main()