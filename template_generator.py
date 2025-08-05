import os
import random
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
import requests

# .env 파일 로드
load_dotenv()

class AdvancedTemplateGenerator:
    def __init__(self):
        self.templates_dir = "templates"
        self.templates = {
            'daytour': '당일치기 여행',
            'food': '맛집 투어', 
            'date': '데이트 코스'
        }
        
        # Gemini API 초기화
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되지 않았습니다.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Gemini API 초기화 완료")
    
    def generate_enhanced_blog_content(self, analysis_results, keywords, template_type='daytour'):
        """AI 강화된 상세 블로그 콘텐츠 생성 (Gemini Vision 통합)"""
        
        print("🤖 AI로 상세 블로그 생성 중...")
        
        # 1. 기본 정보 추출
        user_info = self._extract_user_info(analysis_results, keywords)
        
        # 2. Gemini Vision으로 이미지 내용 분석 시도
        gemini_insights = self._analyze_images_with_gemini(analysis_results, keywords)
        
        # 3. 관련 정보 검색 및 보강
        enhanced_info = self._enhance_with_ai_research(user_info, keywords, template_type, gemini_insights)
        
        # 4. 상세 블로그 생성
        detailed_blog = self._generate_detailed_blog(enhanced_info, template_type)
        
        return detailed_blog
    
    def _analyze_images_with_gemini(self, analysis_results, keywords):
        """Gemini Vision으로 이미지 내용 분석"""
        
        try:
            # EnhancedImageAnalyzer 사용 시도
            from image_analyzer import EnhancedImageAnalyzer
            
            print("🤖 Gemini Vision으로 이미지 내용 분석 중...")
            enhanced_analyzer = EnhancedImageAnalyzer()
            
            if enhanced_analyzer.use_gemini:
                vision_results = enhanced_analyzer.enhanced_analyze_images(analysis_results, keywords)
                
                if vision_results['gemini_analysis'] and 'error' not in vision_results['gemini_analysis']:
                    return {
                        'has_vision_analysis': True,
                        'comprehensive_analysis': vision_results['gemini_analysis'].get('comprehensive_analysis', ''),
                        'image_content': vision_results.get('comprehensive_content', ''),
                        'analyzed_count': vision_results['gemini_analysis'].get('analyzed_count', 0)
                    }
            
            return {'has_vision_analysis': False}
            
        except Exception as e:
            print(f"⚠️ Gemini Vision 분석 건너뜀: {e}")
            return {'has_vision_analysis': False}
    
    def _extract_user_info(self, analysis_results, keywords):
        """사용자 정보 추출 및 정리"""
        
        locations = []
        texts = []
        timestamps = []
        
        for result in analysis_results:
            # GPS 정보
            if result['exif_data'].get('location'):
                locations.append(result['exif_data']['location'])
            
            # 추출된 텍스트
            if result['extracted_text']:
                texts.extend(result['extracted_text'])
            
            # 촬영 시간
            if result['exif_data'].get('datetime'):
                timestamps.append(result['exif_data']['datetime'])
        
        return {
            'keywords': keywords,
            'locations': locations,
            'texts': texts,
            'timestamps': timestamps,
            'image_count': len(analysis_results)
        }
    
    def _enhance_with_ai_research(self, user_info, keywords, template_type, gemini_insights):
        """AI를 활용한 정보 보강 (Gemini Vision 결과 포함)"""
        
        # Gemini Vision 결과가 있으면 활용
        vision_context = ""
        if gemini_insights.get('has_vision_analysis'):
            vision_context = f"""
**이미지 분석 결과 (Gemini Vision)**:
{gemini_insights.get('comprehensive_analysis', '')}

**이미지 기반 콘텐츠**:
{gemini_insights.get('image_content', '')}
"""
        
        research_prompt = f"""
다음 여행 정보를 바탕으로 상세하고 유용한 블로그 콘텐츠를 위한 추가 정보를 생성해주세요.

**사용자 여행 정보:**
- 키워드: {user_info['keywords']}
- 방문 장소: {', '.join(user_info['locations']) if user_info['locations'] else '정보 없음'}
- 추출된 텍스트: {', '.join(user_info['texts'][:10]) if user_info['texts'] else '정보 없음'}
- 이미지 수: {user_info['image_count']}장
- 블로그 타입: {self.templates[template_type]}

{vision_context}

**생성해야 할 추가 정보:**

1. **장소별 상세 정보** (각 100자 이상):
   - 주요 특징과 볼거리
   - 방문 팁과 주의사항
   - 최적 방문 시간

2. **실용적인 정보** (각 50자 이상):
   - 예상 비용 (구체적인 금액)
   - 교통 정보
   - 주변 편의시설

3. **개인적인 경험담** (각 80자 이상):
   - 인상 깊었던 순간들
   - 예상과 달랐던 점들
   - 재방문 의사와 이유

4. **추천 사항** (각 60자 이상):
   - 같이 가면 좋은 장소들
   - 준비물이나 복장
   - 계절별 추천 사항

5. **생생한 묘사** (각 80자 이상):
   - 분위기나 느낌
   - 맛, 향, 소리 등 감각적 표현
   - 사진으로 담지 못한 순간들

6. **이미지 기반 추가 정보** (Vision 분석 결과가 있는 경우):
   - 이미지에서 파악된 특별한 포인트들
   - 시각적으로 확인된 장소나 활동의 세부사항
   - 분위기나 감정적 요소들

각 항목을 구체적이고 생생하게 작성해주세요. 전체 길이는 1000자 이상이 되도록 해주세요.
"""
        
        try:
            response = self.model.generate_content(research_prompt)
            enhanced_content = response.text
            
            return {
                'user_info': user_info,
                'enhanced_content': enhanced_content,
                'template_type': template_type,
                'gemini_insights': gemini_insights
            }
            
        except Exception as e:
            print(f"AI 정보 보강 오류: {e}")
            return {
                'user_info': user_info,
                'enhanced_content': "추가 정보를 생성할 수 없었습니다.",
                'template_type': template_type,
                'gemini_insights': gemini_insights
            }
    
    def _generate_detailed_blog(self, enhanced_info, template_type):
        """상세 블로그 글 생성 (Vision 결과 통합)"""
        
        # Vision 분석 결과 포함 여부 확인
        vision_info = ""
        if enhanced_info['gemini_insights'].get('has_vision_analysis'):
            vision_info = f"""
**이미지에서 파악된 추가 정보:**
{enhanced_info['gemini_insights'].get('image_content', '')}
"""
        
        generation_prompt = f"""
다음 정보를 바탕으로 네이버 블로그 스타일의 상세하고 매력적인 여행 블로그를 작성해주세요.

**기본 정보:**
{enhanced_info['user_info']}

**보강된 정보:**
{enhanced_info['enhanced_content']}

{vision_info}

**블로그 타입:** {self.templates[template_type]}

**작성 요구사항:**
1. **길이**: 최소 1200자 이상의 매우 상세한 내용
2. **구조**: 네이버 블로그 특유의 구조 (볼드, 이모티콘, 단락 구분)
3. **톤**: 친근하고 개인적인 어조
4. **내용**: 실용적이면서도 재미있는 정보

**포함해야 할 요소:**
- 생생한 여행 경험담과 감정 표현
- 구체적인 비용과 실용적 팁
- 이미지에 대한 설명 (실제 사진은 없지만 있다고 가정)
- 다른 여행자들을 위한 상세한 조언
- 개인적인 감상과 진솔한 추천 이유
- 시간대별 일정과 동선 정보

**블로그 스타일:**
- **중요 내용은 볼드 처리**
- 적절한 이모티콘 사용 (😊, 🍽️, 📍, ✨ 등)
- 단락별 소제목 활용
- 친근한 말투 ("~였어요", "~더라구요", "진짜 좋았어요" 등)
- 독자와의 소통을 의식한 문체

**특별 요청**: 
- 이미지 분석 결과가 포함된 경우, 그 정보를 자연스럽게 글에 녹여내기
- 단순한 정보 나열이 아닌, 스토리가 있는 여행기로 작성
- 실제 그 장소에 가본 사람이 쓴 것처럼 생생하게 표현

네이버 블로그에 실제로 올릴 수 있는 완성도 높은 글을 작성해주세요.
"""
        
        try:
            response = self.model.generate_content(generation_prompt)
            return response.text
            
        except Exception as e:
            print(f"블로그 생성 오류: {e}")
            return self._generate_fallback_blog(enhanced_info)
    
    def _generate_fallback_blog(self, enhanced_info):
        """AI 생성 실패시 대체 블로그"""
        
        user_info = enhanced_info['user_info']
        template_type = enhanced_info['template_type']
        
        # 기본 템플릿 로드
        template = self.load_template(template_type)
        
        # 기본 변수들로 생성
        main_location = self.extract_main_location(user_info['keywords'])
        
        template_vars = {
            'title': self.generate_title(user_info['keywords'], template_type),
            'location': main_location,
            'keyword': user_info['keywords'],
            'visited_places': self.format_visited_places(user_info['locations'], user_info['texts']),
            'extracted_texts': self.format_extracted_texts(user_info['texts']),
            'start_time': '오전 9시',
            'activities': self.generate_activities(user_info['keywords']),
            'additional_info': enhanced_info['enhanced_content'][:500] + "\n\n" + 
                             enhanced_info['gemini_insights'].get('image_content', '')[:500],
            'food_review': "방문한 곳들의 음식이 정말 맛있었어요!",
            'restaurant_info': "자세한 정보는 사진을 참고해주세요!",
            'tour_course': "출발 → 주요 관광지 → 식사 → 마무리",
            'total_cost': "약 5만원 내외",
            'couple_points': f"{main_location}는 데이트하기 정말 좋은 곳이에요!",
            'date_timeline': "오전 출발 → 점심 → 오후 활동 → 저녁 → 마무리",
            'special_moments': "함께 보낸 모든 순간이 특별했어요!",
            'date_tips': f"{main_location}에서는 편한 신발을 신고 가세요!"
        }
        
        try:
            return template.format(**template_vars)
        except KeyError as e:
            return f"템플릿 오류: {e}\n\n기본 내용:\n{user_info['keywords']}에 대한 여행 후기입니다."
    
    # 기존 함수들 유지
    def load_template(self, template_type):
        """템플릿 파일 로드"""
        template_path = os.path.join(self.templates_dir, f"{template_type}.txt")
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return self._get_default_template(template_type)
    
    def _get_default_template(self, template_type):
        """기본 템플릿 반환"""
        return f"""
# {{title}}

안녕하세요! 오늘은 {{keyword}}를 다녀온 후기를 올려봅니다! 😊

## 📍 방문한 곳들
{{visited_places}}

## 📸 생생한 후기
{{additional_info}}

정말 알찬 하루였어요! 다음에도 이런 여행을 계획해봐야겠습니다.

#여행 #{{keyword}} #{self.templates[template_type]}
"""
    
    def extract_main_location(self, keywords):
        """키워드에서 주요 위치 추출"""
        locations = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '제주', '경주', '강릉', '전주', '여수']
        for location in locations:
            if location in keywords:
                return location
        return "여행지"
    
    def generate_title(self, keywords, template_type):
        """제목 생성"""
        titles = {
            'daytour': [
                f"⭐ {keywords} 당일치기 완벽 후기! (코스/비용/꿀팁)",
                f"🚗 하루로 충분한 {keywords} 완전정복!",
                f"💯 {keywords} 당일 여행 솔직후기 (사진많음)"
            ],
            'food': [
                f"🍴 {keywords} 맛집투어 완주 후기! (가격/메뉴/웨이팅)",
                f"😋 먹방러가 추천하는 {keywords} 진짜 맛집들",
                f"🔥 {keywords} 숨은 맛집 발견기 (사진多)"
            ],
            'date': [
                f"💕 {keywords} 데이트 완벽 코스 후기! (비용/포토스팟)",
                f"😍 커플이 가면 좋은 {keywords} 달달 데이트",
                f"📸 {keywords} 인생샷 데이트 코스 (사진多)"
            ]
        }
        return random.choice(titles.get(template_type, [f"{keywords} 여행 후기"]))
    
    def format_visited_places(self, locations, texts):
        """방문 장소 포맷팅"""
        places = []
        if locations:
            places.extend([f"📍 {loc}" for loc in locations[:3]])
        if texts:
            places.extend([f"🏪 {text}" for text in texts[:3] if len(text) > 2])
        
        return "\n".join(places) if places else "📍 다양한 멋진 장소들을 방문했어요!"
    
    def format_extracted_texts(self, texts):
        """추출된 텍스트 포맷팅"""
        if not texts:
            return "📷 사진 속 다양한 순간들이 추억으로 남았어요!"
        
        formatted = []
        for text in texts[:5]:
            if len(text.strip()) > 1:
                formatted.append(f"✨ {text.strip()}")
        
        return "\n".join(formatted) if formatted else "📷 특별한 순간들을 카메라에 담았어요!"
    
    def generate_activities(self, keywords):
        """활동 내용 생성"""
        if "맛집" in keywords:
            return "맛집 탐방 및 로컬 푸드 체험"
        elif "데이트" in keywords:
            return "로맨틱한 데이트 코스 체험"
        elif "문화" in keywords:
            return "문화 체험 및 관광지 탐방"
        else:
            return "다양한 여행 체험 및 관광"

# 이전 버전과의 호환성을 위한 클래스
class TemplateGenerator(AdvancedTemplateGenerator):
    """기존 TemplateGenerator와 호환성 유지"""
    
    def generate_blog_content(self, analysis_results, keywords, template_type='daytour'):
        """기존 인터페이스 유지하면서 새 기능 사용"""
        return self.generate_enhanced_blog_content(analysis_results, keywords, template_type)

# 테스트용
def test_enhanced_generator():
    """강화된 템플릿 생성기 테스트"""
    try:
        generator = AdvancedTemplateGenerator()
        print("✅ 고급 템플릿 생성기 초기화 완료!")
        
        # 테스트 데이터
        test_data = [{
            'file_name': 'test.jpg',
            'file_path': '/path/to/test.jpg',
            'exif_data': {'location': '부산 해운대'},
            'extracted_text': ['해운대 해수욕장', '맛집 투어']
        }]
        
        print("🧪 Gemini Vision 통합 테스트...")
        result = generator.generate_enhanced_blog_content(test_data, "부산 여행", "daytour")
        print(f"✅ 생성된 블로그 길이: {len(result)}자")
        print("미리보기:", result[:200] + "...")
        
        return generator
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        print("💡 .env 파일에 GEMINI_API_KEY를 설정했는지 확인해주세요!")
        return None

if __name__ == "__main__":
    test_enhanced_generator()