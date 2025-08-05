import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import easyocr
import exifread
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class ImageAnalyzer:
    def __init__(self):
        # EasyOCR 초기화 (한글, 영어 지원)
        print("OCR 모델 로딩 중... (처음 실행시 시간이 걸릴 수 있습니다)")
        self.reader = easyocr.Reader(['ko', 'en'], gpu=False)
        print("OCR 모델 로딩 완료!")
    
    def extract_exif_data(self, image_path):
        """이미지에서 EXIF 데이터 추출"""
        try:
            with open(image_path, 'rb') as f:
                tags = exifread.process_file(f)
            
            exif_data = {}
            
            # GPS 정보 추출
            if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
                lat = self._convert_to_degrees(tags['GPS GPSLatitude'])
                lon = self._convert_to_degrees(tags['GPS GPSLongitude'])
                
                # 남반구/서반구 처리
                if tags.get('GPS GPSLatitudeRef', 'N') == 'S':
                    lat = -lat
                if tags.get('GPS GPSLongitudeRef', 'E') == 'W':
                    lon = -lon
                    
                exif_data['latitude'] = lat
                exif_data['longitude'] = lon
                exif_data['location'] = f"위도: {lat:.6f}, 경도: {lon:.6f}"
            
            # 촬영 시간
            if 'EXIF DateTimeOriginal' in tags:
                exif_data['datetime'] = str(tags['EXIF DateTimeOriginal'])
            
            # 카메라 정보
            if 'Image Make' in tags:
                exif_data['camera_make'] = str(tags['Image Make'])
            if 'Image Model' in tags:
                exif_data['camera_model'] = str(tags['Image Model'])
                
            return exif_data
            
        except Exception as e:
            print(f"EXIF 추출 오류: {e}")
            return {}
    
    def _convert_to_degrees(self, value):
        """GPS 좌표를 십진수로 변환"""
        d = float(value.values[0].num) / float(value.values[0].den)
        m = float(value.values[1].num) / float(value.values[1].den)
        s = float(value.values[2].num) / float(value.values[2].den)
        return d + (m / 60.0) + (s / 3600.0)
    
    def extract_text_from_image(self, image_path):
        """이미지에서 텍스트 추출 (OCR)"""
        try:
            # OCR 실행
            results = self.reader.readtext(image_path)
            
            # 텍스트만 추출
            extracted_texts = []
            for (bbox, text, confidence) in results:
                if confidence > 0.5:  # 신뢰도 50% 이상만
                    extracted_texts.append(text.strip())
            
            return extracted_texts
            
        except Exception as e:
            print(f"OCR 오류: {e}")
            return []
    
    def analyze_image(self, image_path):
        """이미지 종합 분석"""
        print(f"이미지 분석 중: {image_path}")
        
        result = {
            'file_name': os.path.basename(image_path),
            'file_path': image_path,  # 경로 정보 추가
            'exif_data': self.extract_exif_data(image_path),
            'extracted_text': self.extract_text_from_image(image_path)
        }
        
        return result

class GeminiImageAnalyzer:
    def __init__(self):
        """Gemini Vision 이미지 분석기 초기화"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Gemini Vision 분석기 초기화 완료")
    
    def analyze_single_image(self, image_path, keywords=""):
        """단일 이미지 상세 분석"""
        
        try:
            # 이미지 로드
            image = Image.open(image_path)
            
            analysis_prompt = f"""
이 여행 사진을 자세히 분석해주세요.

**여행 키워드**: {keywords}

다음 관점에서 상세히 분석해주세요:

1. **장소 정보**:
   - 구체적인 장소명이나 랜드마크 (가능한 경우)
   - 장소의 특징과 분위기
   - 실내/실외, 자연/도시 등

2. **활동 내용**:
   - 어떤 활동을 하고 있는지
   - 혼자/친구/가족/연인 등 동행자
   - 여행의 목적 (관광/식사/쇼핑/휴식 등)

3. **음식 정보** (음식 사진인 경우):
   - 구체적인 메뉴명
   - 음식의 특징과 스타일
   - 식당의 분위기나 타입

4. **시간과 날씨**:
   - 촬영 시간대 (아침/점심/저녁/야간)
   - 날씨 상황
   - 계절 추정

5. **분위기와 감정**:
   - 사진에서 느껴지는 전체적인 분위기
   - 즐거움, 로맨틱, 평온함 등의 감정
   - 특별한 순간이나 하이라이트

6. **여행 팁 요소**:
   - 다른 여행자들에게 도움될 정보
   - 주의사항이나 추천사항
   - 베스트 포토스팟 여부

**중요**: 블로그 글에 활용할 수 있는 구체적이고 생생한 정보를 제공해주세요.
"""
            
            response = self.model.generate_content([analysis_prompt, image])
            
            return {
                'gemini_analysis': response.text,
                'image_path': image_path,
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'error': f"Gemini 이미지 분석 실패: {str(e)}",
                'image_path': image_path,
                'status': 'failed'
            }
    
    def analyze_multiple_images(self, image_paths, keywords=""):
        """여러 이미지 통합 분석"""
        
        try:
            # 이미지들 로드
            images = []
            valid_paths = []
            for path in image_paths[:5]:  # 최대 5장
                try:
                    images.append(Image.open(path))
                    valid_paths.append(path)
                except Exception as e:
                    print(f"이미지 로드 실패 {path}: {e}")
            
            if not images:
                return {'error': '분석할 수 있는 이미지가 없습니다.'}
            
            multi_analysis_prompt = f"""
이 여행 사진들을 종합적으로 분석해서 여행 스토리를 만들어주세요.

**여행 키워드**: {keywords}
**이미지 수**: {len(images)}장

다음 관점에서 종합 분석해주세요:

1. **여행 스토리**:
   - 사진들로 보는 여행의 전체적인 흐름
   - 시간 순서나 동선 추정
   - 여행의 하이라이트 순간들

2. **방문 장소들**:
   - 확인되는 구체적인 장소들
   - 각 장소의 특징과 매력포인트
   - 장소들 간의 연관성

3. **여행 스타일**:
   - 어떤 타입의 여행인지 (관광/맛집투어/휴양/체험 등)
   - 여행자의 취향과 관심사
   - 여행의 목적과 컨셉

4. **추천 정보**:
   - 다른 여행자들을 위한 코스 추천
   - 각 장소별 팁과 주의사항
   - 최적 방문 시간이나 순서

5. **감정과 분위기**:
   - 여행 전체의 감정적 톤
   - 특별했던 순간들
   - 기억에 남을 포인트들

6. **실용 정보**:
   - 예상 소요시간과 비용
   - 교통이나 접근성 정보
   - 함께 가면 좋은 사람들 (혼자/친구/가족/연인)

**목표**: 이 사진들을 바탕으로 생생하고 유용한 여행 블로그를 작성할 수 있는 풍부한 정보를 제공해주세요.
"""
            
            # 모든 이미지와 프롬프트를 함께 전달
            content = [multi_analysis_prompt] + images
            response = self.model.generate_content(content)
            
            return {
                'comprehensive_analysis': response.text,
                'analyzed_count': len(images),
                'analyzed_paths': valid_paths,
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'error': f"통합 이미지 분석 실패: {str(e)}",
                'status': 'failed'
            }
    
    def generate_image_based_content(self, image_paths, keywords, analysis_result):
        """이미지 분석 결과를 바탕으로 블로그 콘텐츠 생성"""
        
        content_prompt = f"""
다음 이미지 분석 결과를 바탕으로 여행 블로그의 핵심 내용을 생성해주세요.

**키워드**: {keywords}
**이미지 분석 결과**:
{analysis_result.get('comprehensive_analysis', '')}

다음 요소들을 포함한 블로그 콘텐츠를 만들어주세요:

1. **여행 하이라이트**: 가장 인상적이었던 순간들
2. **장소별 상세 후기**: 각 방문지의 특징과 느낌
3. **맛집 정보**: 음식과 식당에 대한 구체적 정보  
4. **실용적 팁**: 다른 여행자들을 위한 조언
5. **감성적 묘사**: 분위기와 감정을 담은 표현들
6. **추천 사유**: 왜 이곳을 추천하는지

**조건**:
- 800자 이상의 상세한 내용
- 생생하고 구체적인 표현 사용
- 실제 경험한 것처럼 자연스럽게 작성
- 다른 여행자들에게 도움이 되는 정보 포함

블로그 글의 핵심이 될 수 있는 풍부한 내용을 만들어주세요.
"""
        
        try:
            response = self.model.generate_content(content_prompt)
            return response.text
        except Exception as e:
            return f"콘텐츠 생성 실패: {str(e)}"

class EnhancedImageAnalyzer(ImageAnalyzer):
    """기존 분석기 + Gemini Vision 통합"""
    
    def __init__(self):
        super().__init__()
        try:
            self.gemini_analyzer = GeminiImageAnalyzer()
            self.use_gemini = True
            print("✅ Gemini Vision 기능 활성화")
        except Exception as e:
            print(f"⚠️ Gemini Vision 비활성화: {e}")
            self.use_gemini = False
    
    def enhanced_analyze_images(self, analysis_results, keywords=""):
        """강화된 이미지 분석 (기존 + Gemini Vision)"""
        
        results = {
            'basic_analysis': analysis_results,
            'gemini_analysis': None,
            'comprehensive_content': ""
        }
        
        # Gemini Vision 분석 (가능한 경우)
        if self.use_gemini:
            print("🤖 Gemini Vision으로 이미지 내용 분석 중...")
            
            # 이미지 경로들 추출
            image_paths = []
            for result in analysis_results:
                if 'file_path' in result:
                    image_paths.append(result['file_path'])
            
            if image_paths:
                gemini_result = self.gemini_analyzer.analyze_multiple_images(image_paths, keywords)
                results['gemini_analysis'] = gemini_result
                
                # 통합 콘텐츠 생성
                if 'error' not in gemini_result:
                    print("✍️ 이미지 기반 상세 콘텐츠 생성 중...")
                    content = self.gemini_analyzer.generate_image_based_content(
                        image_paths, keywords, gemini_result
                    )
                    results['comprehensive_content'] = content
                    print("✅ Gemini Vision 분석 완료!")
                else:
                    print(f"⚠️ Gemini Vision 분석 실패: {gemini_result['error']}")
        
        return results

# 테스트용 함수
def test_analyzer():
    """분석기 테스트"""
    try:
        # 기본 분석기 테스트
        analyzer = ImageAnalyzer()
        print("✅ 기본 이미지 분석기 준비 완료!")
        
        # 강화된 분석기 테스트
        enhanced_analyzer = EnhancedImageAnalyzer()
        print("✅ 강화된 이미지 분석기 준비 완료!")
        
        return enhanced_analyzer
        
    except Exception as e:
        print(f"❌ 분석기 초기화 실패: {e}")
        return None

if __name__ == "__main__":
    test_analyzer()