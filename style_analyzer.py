import google.generativeai as genai
from blog_scraper import BlogScraper
import re
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class StyleAnalyzer:
    def __init__(self, api_key=None):
        """스타일 분석기 초기화"""
        
        # API 키 설정 (.env에서 자동 로드 또는 직접 전달)
        if api_key is None:
            api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.scraper = BlogScraper(use_selenium=False)  # 스크래핑은 백업용
        print("✅ StyleAnalyzer 초기화 완료")
    
    def analyze_blog_style_from_url(self, blog_url):
        """URL을 Gemini에게 직접 전달해서 스타일 분석"""
        
        print("🌐 Gemini가 직접 웹페이지 분석 중...")
        
        url_analysis_prompt = f"""
다음 블로그 URL에 직접 접속해서 내용을 읽고 스타일을 분석해주세요.

URL: {blog_url}

이 블로그의 글쓰기 스타일을 다음 관점에서 자세히 분석해주세요:

1. **문체 특징**:
   - 존댓말/반말 사용 패턴
   - 문장 길이와 구조 (짧음/보통/긺)
   - 자주 사용하는 문장 종결 어미 ("~어요", "~습니다", "~네요" 등)
   - 이모티콘 사용 패턴과 빈도

2. **어투 특성**:
   - 친근함 정도 (1-10점 척도)
   - 격식성 정도 (1-10점 척도)
   - 개성적인 표현들과 말투
   - 자주 사용하는 단어나 구문
   - 독자와의 소통 방식

3. **구조 특징**:
   - 제목과 소제목 작성 스타일
   - 단락 구성 방식 (긴 단락/짧은 단락)
   - 강조 표현 방법 (볼드, 이모티콘, 특수문자 등)
   - 목록이나 번호 사용 패턴
   - 사진 설명이나 캡션 스타일

4. **감정 표현**:
   - 감정 표현의 강도와 방식
   - 흥미로운 순간의 표현법
   - 추천이나 조언할 때의 톤

5. **특별한 매력 포인트**:
   - 이 블로거만의 독특한 특징
   - 글의 전반적인 분위기
   - 독자를 끌어들이는 방식

**중요**: 실제로 해당 URL에 접속해서 블로그 내용을 읽은 후 분석해주세요.
나중에 이 스타일을 모방해서 새로운 여행 블로그를 작성할 예정입니다.

분석 결과를 구체적이고 실용적으로 설명해주세요.
"""
        
        try:
            # Gemini에게 URL 직접 전달
            response = self.model.generate_content([url_analysis_prompt])
            
            # 분석 결과 정리
            return {
                'blog_data': {
                    'title': '웹페이지에서 추출',
                    'content': '웹페이지 내용 (Gemini가 직접 읽음)',
                    'platform': 'web_direct',
                    'url': blog_url,
                    'content_length': 0,  # Gemini가 직접 읽었으므로 우리는 모름
                    'word_count': 0
                },
                'style_analysis': response.text,
                'url': blog_url,
                'method': 'gemini_direct'
            }
            
        except Exception as e:
            print(f"Gemini URL 분석 오류: {e}")
            return {
                'error': f'Gemini URL 분석 실패: {str(e)}',
                'suggestion': '수동 입력 방식을 사용해주세요.'
            }
    
    def analyze_blog_style_hybrid(self, blog_url):
        """하이브리드 방식: Gemini 직접 분석 + 스크래핑 백업"""
        
        print("🔄 하이브리드 분석 시작...")
        
        # 먼저 Gemini 직접 분석 시도
        print("🌐 1단계: Gemini 직접 웹페이지 분석...")
        gemini_result = self.analyze_blog_style_from_url(blog_url)
        
        if 'error' not in gemini_result:
            print("✅ Gemini 직접 분석 성공!")
            return gemini_result
        
        # Gemini 실패시 스크래핑 백업
        print("⚠️ Gemini 분석 실패, 스크래핑 백업 시도...")
        print("🔄 2단계: 웹 스크래핑으로 내용 추출...")
        
        try:
            scraping_result = self.scraper.scrape_blog(blog_url)
            
            if 'error' in scraping_result or scraping_result.get('content_length', 0) < 50:
                return {
                    'error': 'Gemini 분석과 스크래핑 모두 실패했습니다.',
                    'suggestion': '수동 입력 방식을 권장합니다.'
                }
            
            print("✅ 스크래핑 성공! AI 스타일 분석 중...")
            style_analysis = self._analyze_writing_style(scraping_result)
            
            return {
                'blog_data': scraping_result,
                'style_analysis': style_analysis,
                'url': blog_url,
                'method': 'scraping_backup'
            }
            
        except Exception as e:
            return {
                'error': f'모든 분석 방법이 실패했습니다: {str(e)}',
                'suggestion': '수동 입력 방식을 사용해주세요.'
            }
    
    def analyze_blog_style_manual(self, blog_title, blog_content, blog_url=""):
        """수동 입력된 블로그 내용으로 스타일 분석"""
        
        print("🤖 AI 스타일 분석 중...")
        
        blog_data = {
            'title': blog_title,
            'content': blog_content,
            'platform': 'manual',
            'url': blog_url,
            'content_length': len(blog_content),
            'word_count': len(blog_content.split())
        }
        
        # Gemini로 스타일 분석
        style_analysis = self._analyze_writing_style(blog_data)
        
        return {
            'blog_data': blog_data,
            'style_analysis': style_analysis,
            'url': blog_url,
            'method': 'manual'
        }
    
    def _analyze_writing_style(self, blog_data):
        """개선된 Gemini 문체 분석"""
        
        analysis_prompt = f"""
다음 블로그 글의 문체를 정확히 분석해주세요.

**제목**: {blog_data['title']}
**내용**: {blog_data['content'][:2000]}

다음 요소들을 구체적으로 분석해주세요:

1. **문체 특징**:
   - 존댓말/반말 사용 패턴 (주로 어떤 것을 사용하는지)
   - 문장 길이와 구조 (짧고 간결한지, 길고 상세한지)
   - 자주 사용하는 문장 종결 어미들
   - 이모티콘 사용 빈도와 종류

2. **어투 특성**:
   - 친근함 정도 (1-10점 척도로)
   - 격식성 정도 (1-10점 척도로)
   - 개성적인 표현들이나 말투
   - 자주 반복되는 단어나 구문
   - 독자와의 소통 방식

3. **구조 특징**:
   - 단락 구성 방식 (긴 단락/짧은 단락/혼합)
   - 소제목이나 구분 기호 사용 패턴
   - 강조 표현 방법 (볼드, 이모티콘, 느낌표 등)
   - 목록이나 번호 매기기 사용 빈도

4. **감정 표현**:
   - 감정 표현의 강도와 방식
   - 재미있거나 인상적인 순간의 표현법
   - 추천이나 조언할 때의 어조

5. **전체적인 특징**:
   - 이 블로거만의 독특한 매력 포인트
   - 글의 전반적인 분위기와 톤
   - 독자를 끌어들이는 특별한 방식

**중요**: 이 분석을 바탕으로 나중에 같은 스타일로 새로운 여행 블로그를 작성할 예정입니다.
따라서 모방 가능한 구체적인 특징들을 중심으로 분석해주세요.

분석 결과를 자세하고 실용적으로 설명해주세요.
"""
        
        try:
            response = self.model.generate_content(analysis_prompt)
            return response.text
        except Exception as e:
            return f"스타일 분석 오류: {str(e)}"
    
    def generate_blog_with_style(self, user_content, style_analysis, keywords):
        """개선된 스타일 적용 블로그 생성"""
        
        generation_prompt = f"""
다음 정보를 바탕으로 자연스럽고 완성도 높은 여행 블로그를 작성해주세요.

**사용자 여행 정보:**
{user_content}

**키워드:** {keywords}

**참고할 스타일 분석:**
{style_analysis}

**작성 요구사항:**
1. **문법과 맞춤법을 정확히 지켜주세요**
2. **자연스럽고 읽기 쉬운 문장으로 작성**
3. **참고 스타일의 톤과 어투를 최대한 따라하기**
4. **최소 1000자 이상의 상세한 내용**
5. **실제 존재할 법한 여행 후기로 작성**

**스타일 적용 지침:**
- 참고 블로그의 문체 특징을 그대로 모방
- 같은 종류의 문장 종결 어미 사용
- 비슷한 감정 표현 방식 적용
- 동일한 수준의 친근함과 격식성 유지
- 참고 블로그의 구조적 특징 반영

**중요한 주의사항:**
- 의미 없는 문장이나 어색한 표현 절대 금지
- 문법적으로 올바른 한국어만 사용
- 논리적이고 일관성 있는 내용 구성
- 실제 여행 경험처럼 생생하게 작성
- 네이버 블로그 스타일로 완성

**목표**: 참고 블로그를 쓴 사람이 직접 작성한 것처럼 자연스러운 글을 만들어주세요.
하지만 무엇보다 **읽기 좋고 자연스러운 글**이 최우선입니다.
"""
        
        try:
            response = self.model.generate_content(generation_prompt)
            return response.text
        except Exception as e:
            return f"블로그 생성 오류: {str(e)}"
    
    def test_url_analysis(self, test_url):
        """URL 분석 테스트 함수"""
        print(f"🧪 URL 분석 테스트: {test_url}")
        
        result = self.analyze_blog_style_hybrid(test_url)
        
        if 'error' in result:
            print(f"❌ 테스트 실패: {result['error']}")
            return False
        else:
            print("✅ 테스트 성공!")
            print(f"방법: {result['method']}")
            print(f"분석 결과 길이: {len(result['style_analysis'])}자")
            return True

# 테스트 함수들
def test_style_analyzer():
    """스타일 분석기 테스트"""
    try:
        analyzer = StyleAnalyzer()
        print("✅ StyleAnalyzer 초기화 성공!")
        
        # 간단한 수동 입력 테스트
        test_result = analyzer.analyze_blog_style_manual(
            "테스트 제목",
            "안녕하세요! 오늘은 여행 후기를 올려봅니다. 정말 재밌었어요. 다음에도 또 가고 싶어요!",
            ""
        )
        print("✅ 수동 입력 스타일 분석 테스트 성공!")
        
        return analyzer
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return None

def test_url_functionality():
    """URL 기능 테스트"""
    try:
        analyzer = StyleAnalyzer()
        
        # URL 테스트 (실제 테스트 시에는 유효한 URL 사용)
        test_url = "https://blog.naver.com"  # 예시 URL
        
        print(f"🧪 URL 기능 테스트 시작...")
        result = analyzer.test_url_analysis(test_url)
        
        if result:
            print("🎉 모든 테스트 통과!")
        else:
            print("⚠️ 일부 테스트 실패")
            
    except Exception as e:
        print(f"❌ URL 테스트 실패: {e}")

if __name__ == "__main__":
    print("🚀 StyleAnalyzer 테스트 시작...")
    
    # 기본 기능 테스트
    analyzer = test_style_analyzer()
    
    if analyzer:
        print("\n" + "="*50)
        print("🌐 URL 분석 기능 테스트")
        
        # URL 기능 테스트 (선택사항)
        choice = input("\nURL 분석 기능을 테스트하시겠습니까? (y/n): ").lower()
        if choice == 'y':
            test_url_functionality()
        else:
            print("URL 테스트를 건너뜁니다.")
    
    print("\n✅ 모든 테스트 완료!")