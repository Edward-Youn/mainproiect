import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

class BlogScraper:
    def __init__(self, use_selenium=True):
        self.use_selenium = use_selenium
        
        # 일반 requests 세션
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Selenium 웹드라이버 (필요시)
        self.driver = None
        if use_selenium:
            self._init_selenium_driver()
    
    def _init_selenium_driver(self):
        """Selenium 웹드라이버 초기화"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 브라우저 창 숨기기
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✅ Selenium 웹드라이버 초기화 완료")
            
        except Exception as e:
            print(f"⚠️ Selenium 초기화 실패: {e}")
            print("일반 스크래핑 모드로 전환합니다.")
            self.use_selenium = False
    
    def scrape_naver_blog_selenium(self, url):
        """Selenium을 사용한 네이버 블로그 스크래핑"""
        if not self.driver:
            return {'error': 'Selenium 드라이버가 초기화되지 않았습니다.'}
        
        try:
            print("🔄 Selenium으로 페이지 로딩 중...")
            self.driver.get(url)
            
            # 페이지 로딩 대기
            time.sleep(3)
            
            # JavaScript 실행 완료 대기
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # 추가 대기 (동적 콘텐츠 로딩)
            time.sleep(2)
            
            # 페이지 소스 가져오기
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 제목 추출 (다양한 선택자 시도)
            title = ""
            title_selectors = [
                'h3.se_title',
                '.se-title-text', 
                '.se_title',
                '.pcol1 .se_title',
                '.title_area .title',
                'h1', 'h2', 'h3'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.get_text().strip():
                    title = title_elem.get_text().strip()
                    break
            
            # 본문 추출 (더 광범위한 선택자)
            content = ""
            content_selectors = [
                '.se-main-container',
                '.se_component_wrap', 
                '#postViewArea',
                '.se-viewer',
                '.se_doc_viewer',
                '[class*="se-"]',
                '.post_ct',
                '.blog_content'
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # 모든 텍스트 추출 (태그 제거)
                    content = content_elem.get_text(separator='\n', strip=True)
                    if len(content) > 100:  # 충분한 내용이 있으면 사용
                        break
            
            # 여전히 내용이 부족하면 전체 body에서 추출
            if len(content) < 100:
                body = soup.find('body')
                if body:
                    content = body.get_text(separator='\n', strip=True)
            
            print(f"📝 추출된 내용 길이: {len(content)}자")
            
            return self.clean_text({
                'title': title or "제목 없음",
                'content': content,
                'platform': 'naver',
                'url': url
            })
            
        except Exception as e:
            return {'error': f"Selenium 스크래핑 오류: {str(e)}"}
    
    def scrape_blog(self, url):
        """통합 블로그 스크래핑 (Selenium 우선)"""
        if not self.is_supported_blog(url):
            return {'error': '지원되지 않는 블로그 플랫폼입니다.'}
        
        domain = urlparse(url).netloc.lower()
        
        # 네이버 블로그는 Selenium 사용
        if 'blog.naver.com' in domain:
            if self.use_selenium:
                result = self.scrape_naver_blog_selenium(url)
                # Selenium 결과가 충분하지 않으면 일반 스크래핑도 시도
                if 'error' not in result and result.get('content_length', 0) > 100:
                    return result
                else:
                    print("⚠️ Selenium 결과가 부족합니다. 일반 스크래핑을 시도합니다.")
            
            return self.scrape_naver_blog_fallback(url)
        
        elif 'tistory.com' in domain:
            return self.scrape_tistory_blog(url)
        else:
            return self.general_scrape(url)
    
    def scrape_naver_blog_fallback(self, url):
        """네이버 블로그 일반 스크래핑 (fallback)"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 더 많은 선택자 시도
            title = ""
            content = ""
            
            # 전체 텍스트에서 의미있는 부분 추출
            all_text = soup.get_text()
            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
            
            # 긴 줄들을 content로 사용 (광고나 메뉴가 아닌)
            content_lines = []
            for line in lines:
                if len(line) > 10 and not any(keyword in line.lower() for keyword in 
                    ['copyright', '저작권', 'naver', '네이버', 'menu', '메뉴', 'login', '로그인']):
                    content_lines.append(line)
            
            content = '\n'.join(content_lines[:50])  # 상위 50줄만
            
            return self.clean_text({
                'title': title or "제목 추출 실패",
                'content': content,
                'platform': 'naver_fallback',
                'url': url
            })
            
        except Exception as e:
            return {'error': f"일반 스크래핑 오류: {str(e)}"}
    
    def is_supported_blog(self, url):
        """지원되는 블로그 플랫폼인지 확인"""
        domain = urlparse(url).netloc.lower()
        supported_domains = [
            'blog.naver.com',
            'tistory.com',
            'velog.io',
            'brunch.co.kr'
        ]
        return any(supported in domain for supported in supported_domains)
    
    def scrape_tistory_blog(self, url):
        """티스토리 블로그 스크래핑 (기존 코드 유지)"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            title = ""
            title_selectors = ['.title', '.entry-title', 'h1', 'h2', '.post-title']
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text().strip()
                    break
            
            content = ""
            content_selectors = ['.entry-content', '.post-content', '.article', '.content']
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem.get_text()
                    break
            
            return self.clean_text({
                'title': title,
                'content': content,
                'platform': 'tistory',
                'url': url
            })
            
        except Exception as e:
            return {'error': f"티스토리 스크래핑 오류: {str(e)}"}
    
    def general_scrape(self, url):
        """일반 웹페이지 스크래핑"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            title = soup.title.string if soup.title else ""
            
            content_selectors = ['article', 'main', '[class*="content"]', '[class*="post"]']
            content = ""
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem.get_text()
                    break
            
            if not content:
                content = soup.get_text()
            
            return self.clean_text({
                'title': title,
                'content': content,
                'platform': 'general',
                'url': url
            })
            
        except Exception as e:
            return {'error': f"일반 스크래핑 오류: {str(e)}"}
    
    def clean_text(self, data):
        """텍스트 정리"""
        if 'error' in data:
            return data
        
        title = re.sub(r'\s+', ' ', data['title']).strip()
        
        content = data['content']
        content = re.sub(r'\n\s*\n', '\n', content)
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        # 너무 긴 경우 자르기
        if len(content) > 5000:
            content = content[:5000] + "..."
        
        return {
            'title': title,
            'content': content,
            'platform': data['platform'],
            'url': data['url'],
            'content_length': len(content),
            'word_count': len(content.split())
        }
    
    def __del__(self):
        """웹드라이버 종료"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

# 테스트 함수
def test_scraper():
    """개선된 스크래퍼 테스트"""
    print("🔧 개선된 블로그 스크래퍼 테스트")
    
    scraper = BlogScraper(use_selenium=True)
    
    test_url = input("테스트할 블로그 URL을 입력하세요: ")
    
    if test_url:
        print("🔄 Selenium으로 스크래핑 중...")
        result = scraper.scrape_blog(test_url)
        
        if 'error' in result:
            print(f"❌ 오류: {result['error']}")
        else:
            print("✅ 스크래핑 성공!")
            print(f"제목: {result['title']}")
            print(f"플랫폼: {result['platform']}")
            print(f"내용 길이: {result['content_length']}자")
            print(f"단어 수: {result['word_count']}개")
            print(f"\n내용 미리보기:\n{result['content'][:500]}...")

if __name__ == "__main__":
    test_scraper()