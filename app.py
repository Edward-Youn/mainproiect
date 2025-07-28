# -*- coding: utf-8 -*-
"""
뉴스 자동화 시스템 - 메인 애플리케이션
RSS 피드를 활용한 뉴스 수집, 요약 및 PDF 보고서 생성
"""

import streamlit as st
import feedparser
import requests
from bs4 import BeautifulSoup
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import time
import re
from datetime import datetime
import io
import nltk
from dotenv import load_dotenv
from collections import Counter

# 환경변수 로드
load_dotenv()

# NLTK 데이터 다운로드 (최초 실행시)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class NewsCollector:
    """RSS 피드에서 뉴스를 수집하고 크롤링하는 클래스 (다중 RSS 지원)"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 매일경제 + 연합뉴스 + SBS + JTBC 뉴스 RSS 피드 목록
        self.rss_feeds = {
            # 매일경제 RSS
            "매경_헤드라인": "https://www.mk.co.kr/rss/30000001/",
            "매경_경제": "https://www.mk.co.kr/rss/30100041/",
            "매경_정치": "https://www.mk.co.kr/rss/30200030/",
            "매경_사회": "https://www.mk.co.kr/rss/50400012/",
            "매경_국제": "https://www.mk.co.kr/rss/30300018/",
            "매경_증권": "https://www.mk.co.kr/rss/50200011/",
            "매경_부동산": "https://www.mk.co.kr/rss/50300009/",
            "매경_문화연예": "https://www.mk.co.kr/rss/30000023/",
            "매경_게임": "https://www.mk.co.kr/rss/50700001/",
            "매경_스포츠": "https://www.mk.co.kr/rss/71000001/",
            "매경_전체": "https://www.mk.co.kr/rss/40300001/",
            
            # 연합뉴스 RSS
            "연합뉴스_종합": "https://www.yna.co.kr/rss/news.xml",
            "연합뉴스TV": "http://www.yonhapnewstv.co.kr/browse/feed/",
            "연합뉴스TV_문화": "http://www.yonhapnewstv.co.kr/category/news/culture/feed/",
            "연합뉴스TV_국제": "http://www.yonhapnewstv.co.kr/category/news/international/feed/",
            "연합뉴스TV_정치": "http://www.yonhapnewstv.co.kr/category/news/politics/feed/",
            "연합뉴스TV_경제": "http://www.yonhapnewstv.co.kr/category/news/economy/feed/",
            
            # SBS 뉴스 RSS
            "SBS_헤드라인": "https://news.sbs.co.kr/news/headlineRssFeed.do?plink=RSSREADER",
            "SBS_토픽": "https://news.sbs.co.kr/news/TopicRssFeed.do?plink=RSSREADER",
            "SBS_모닝와이드": "https://news.sbs.co.kr/news/ReplayRssFeed.do?prog_cd=R2&plink=RSSREADER",
            "SBS_8뉴스": "https://news.sbs.co.kr/news/ReplayRssFeed.do?prog_cd=RN&plink=RSSREADER",
            "SBS_SBS뉴스": "https://news.sbs.co.kr/news/ReplayRssFeed.do?prog_cd=RS&plink=RSSREADER",
            
            # JTBC 뉴스 RSS
            "JTBC_뉴스룸": "https://news-ex.jtbc.co.kr/v1/get/rss/program/NG10000013",
            "JTBC_아침앤": "https://news-ex.jtbc.co.kr/v1/get/rss/program/NG10000015",
            "JTBC_정치부회의": "https://news-ex.jtbc.co.kr/v1/get/rss/program/NG10000002"
            
        }
    
    def get_rss_feeds(self, rss_url, category_name=""):
        """RSS 피드에서 기사 목록을 가져옴"""
        try:
            feed = feedparser.parse(rss_url)
            articles = []
            
            for entry in feed.entries:
                article = {
                    'title': entry.title,
                    'link': entry.link,
                    'description': entry.get('description', ''),
                    'published': entry.get('published', ''),
                    'summary': entry.get('summary', ''),
                    'category': category_name
                }
                articles.append(article)
            
            return articles
        except Exception as e:
            st.warning(f"{category_name} RSS 피드 수집 중 오류 발생: {str(e)}")
            return []
    
    def get_all_rss_feeds(self, selected_categories=None):
        """선택된 모든 RSS 피드에서 기사 목록을 가져옴 (간단한 진행률 표시)"""
        if selected_categories is None:
            selected_categories = list(self.rss_feeds.keys())
        
        all_articles = []
        total_categories = len(selected_categories)
        
        # 간단한 진행률 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text(f"RSS 피드 수집 중... (0/{total_categories})")
        
        for i, category in enumerate(selected_categories):
            if category in self.rss_feeds:
                # 진행률 업데이트 (세부 내용 없이)
                progress_bar.progress((i + 1) / total_categories)
                status_text.text(f"RSS 피드 수집 중... ({i+1}/{total_categories})")
                
                rss_url = self.rss_feeds[category]
                articles = self.get_rss_feeds(rss_url, category)
                
                if articles:
                    all_articles.extend(articles)
                
                # RSS 서버 부하 방지
                time.sleep(0.3)  # 딜레이 단축
        
        # 진행률 바 제거
        progress_bar.empty()
        status_text.empty()
        
        # 중복 기사 제거 (URL 기준)
        unique_articles = []
        seen_urls = set()
        
        for article in all_articles:
            if article['link'] not in seen_urls:
                unique_articles.append(article)
                seen_urls.add(article['link'])
        
        return unique_articles
    
    def filter_by_keywords(self, articles, keywords):
        """키워드로 기사 필터링 (간단한 결과 표시)"""
        filtered_articles = []
        keywords_lower = [kw.lower() for kw in keywords]
        
        for article in articles:
            title_lower = article['title'].lower()
            desc_lower = article['description'].lower()
            
            # 제목이나 설명에 키워드가 포함된 기사만 선택
            if any(keyword in title_lower or keyword in desc_lower for keyword in keywords_lower):
                filtered_articles.append(article)
        
        return filtered_articles
    
    def crawl_article_content(self, url):
        """개별 기사의 본문을 크롤링 (다중 언론사 지원)"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 언론사별 기사 본문 선택자
            content_selectors = []
            
            # 매일경제
            if 'mk.co.kr' in url:
                content_selectors = [
                    '.news_cnt_detail_wrap',
                    '.art_txt',
                    '.article_body',
                    '.news_content'
                ]
            
            # 연합뉴스
            elif 'yna.co.kr' in url or 'yonhapnewstv.co.kr' in url:
                content_selectors = [
                    '.story-news p',
                    '.article-text',
                    '.story-body',
                    '.news-content p'
                ]
            
            # SBS 뉴스
            elif 'sbs.co.kr' in url:
                content_selectors = [
                    '.text_area',
                    '.article_content',
                    '.news_content',
                    '.article-body p'
                ]
            
            # JTBC 뉴스
            elif 'jtbc.co.kr' in url:
                content_selectors = [
                    '.article_content',
                    '.news_content',
                    '.article-body',
                    '.content_text',
                    '.article_txt'
                ]
            
            # 일반적인 선택자 (fallback)
            content_selectors.extend([
                'div[class*="content"]',
                'div[class*="article"]',
                '.content',
                '.article',
                'article'
            ])
            
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = ' '.join([elem.get_text(strip=True) for elem in elements])
                    if len(content) > 50:  # 충분한 내용이 있을 때만
                        break
            
            # 최종 fallback: p 태그에서 본문 추출
            if not content or len(content) < 50:
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            # 광고나 불필요한 텍스트 제거 (강화된 버전)
            if content:
                # 기자 정보, 이메일, 저작권 등 제거
                content = re.sub(r'[가-힣]*\s*기자.*?@.*?\.[a-z]{2,}', '', content)
                content = re.sub(r'저작권.*?금지', '', content)
                content = re.sub(r'무단.*?금지', '', content)
                content = re.sub(r'\[.*?앵커.*?\]', '', content)
                content = re.sub(r'\[.*?리포트.*?\]', '', content)
                
                # 앱 관련 광고 텍스트 제거
                content = re.sub(r'jebo23.*?친구\s*추가.*?@.*?\..*?[가-힣]*', '', content)
                content = re.sub(r'라인\s*앱에서.*?친구\s*추가', '', content)
                content = re.sub(r'좋아요\d+응원해요\d+후속\s*원해요\d+', '', content)
                content = re.sub(r'ADVERTISEMENT', '', content)
                content = re.sub(r'광고', '', content)
                
                # 사진/이미지 출처 관련 텍스트 제거
                content = re.sub(r'사진\s*=\s*[^\n]*', '', content)
                content = re.sub(r'출처\s*:\s*[^\n]*', '', content)
                content = re.sub(r'제공\s*=\s*[^\n]*', '', content)
                content = re.sub(r'이미지\s*=\s*[^\n]*', '', content)
                content = re.sub(r'사진제공\s*[^\n]*', '', content)
                content = re.sub(r'자료사진\s*[^\n]*', '', content)
                content = re.sub(r'연합뉴스\s*자료사진', '', content)
                content = re.sub(r'뉴시스\s*자료사진', '', content)
                content = re.sub(r'게티이미지\s*뱅크', '', content)
                content = re.sub(r'AFP\s*연합뉴스', '', content)
                content = re.sub(r'로이터\s*연합뉴스', '', content)
                
                # 소셜미디어 관련 텍스트 제거
                content = re.sub(r'페이스북.*?공유', '', content)
                content = re.sub(r'트위터.*?공유', '', content)
                content = re.sub(r'카카오톡.*?공유', '', content)
                content = re.sub(r'네이버.*?공유', '', content)
                
                # 구독/알림 관련 텍스트 제거
                content = re.sub(r'구독.*?알림', '', content)
                content = re.sub(r'팔로우.*?하기', '', content)
                content = re.sub(r'더\s*많은.*?뉴스', '', content)
                
                # 웹사이트 UI 및 제보 관련 텍스트 제거
                content = re.sub(r'닫기', '', content)
                content = re.sub(r'제보는.*?카카오톡', '', content)
                content = re.sub(r'제보.*?접수', '', content)
                content = re.sub(r'뉴스\s*제보', '', content)
                content = re.sub(r'독자\s*제보', '', content)
                content = re.sub(r'시청자\s*제보', '', content)
                content = re.sub(r'취재\s*요청', '', content)
                content = re.sub(r'문의.*?연락처', '', content)
                content = re.sub(r'홈페이지.*?바로가기', '', content)
                content = re.sub(r'모바일.*?버전', '', content)
                content = re.sub(r'PC.*?버전', '', content)
                content = re.sub(r'전체.*?메뉴', '', content)
                content = re.sub(r'메뉴.*?닫기', '', content)
                content = re.sub(r'로그인.*?회원가입', '', content)
                content = re.sub(r'회원.*?서비스', '', content)
                
                # 연속된 공백 정리
                content = re.sub(r'\s+', ' ', content)
                content = content.strip()
                
            return content[:2500] if content else "본문을 가져올 수 없습니다."
            
        except Exception as e:
            return f"크롤링 오류: {str(e)}"
    
    def collect_news_with_content(self, keywords):
        """키워드 기반으로 모든 RSS에서 뉴스를 자동 수집하고 본문까지 크롤링"""
        
        # 1단계: 모든 RSS에서 기사 목록 가져오기 (자동으로 전체 수집)
        st.info("🔄 1단계: 모든 RSS 피드에서 기사 목록 수집 중...")
        all_articles = self.get_all_rss_feeds(list(self.rss_feeds.keys()))  # 모든 카테고리 자동 수집
        
        if not all_articles:
            return []
        
        # 2단계: 키워드로 필터링
        st.info("🔍 2단계: 키워드 매칭 중...")
        filtered_articles = self.filter_by_keywords(all_articles, keywords)
        
        if not filtered_articles:
            st.warning("😅 키워드와 매칭되는 기사가 없습니다.")
            return []
        
        # 3단계: 각 기사의 본문 크롤링
        st.info(f"📰 3단계: {len(filtered_articles)}개 기사 본문 크롤링 중...")
        
        # 진행상황 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, article in enumerate(filtered_articles):
            status_text.text(f'기사 크롤링 중... {i+1}/{len(filtered_articles)} - {article["category"]}')
            progress_bar.progress((i + 1) / len(filtered_articles))
            
            content = self.crawl_article_content(article['link'])
            article['content'] = content
            
            # 서버 부하 방지를 위한 딜레이
            time.sleep(1)
        
        progress_bar.empty()
        status_text.empty()
        
        return filtered_articles

class TextProcessor:
    """텍스트 요약 및 키워드 추출 클래스 (개선된 버전)"""
    
    def __init__(self, language='korean'):
        self.language = language
        try:
            from sumy.nlp.stemmers import Stemmer
            from sumy.summarizers.lex_rank import LexRankSummarizer
            from sumy.utils import get_stop_words
            
            self.stemmer = Stemmer(language)
            self.summarizer = LexRankSummarizer(self.stemmer)
            self.summarizer.stop_words = get_stop_words(language)
            self.use_sumy = True
        except Exception as e:
            st.warning(f"Sumy 초기화 실패: {str(e)}. 간단한 요약 방식을 사용합니다.")
            self.use_sumy = False
    
    def simple_summarize(self, text, max_sentences=3):
        """한국어 최적화된 간단한 문장 기반 요약"""
        if not text or len(text.strip()) < 50:
            return "요약할 내용이 부족합니다."
        
        # 한국어 문장 분리 (더 정확한 방법)
        sentences = []
        # 한국어 문장 끝 표시: ., !, ?, 다, 었다, 였다, ㅂ니다, 습니다 등
        sentence_endings = re.split(r'[.!?]|다\s|었다\s|였다\s|습니다\s|ㅂ니다\s', text)
        
        for sentence in sentence_endings:
            sentence = sentence.strip()
            # 너무 짧은 문장, 기자 서명, 사진 출처, UI 관련 문장 제외
            if (len(sentence) > 15 and 
                '기자' not in sentence[:10] and
                '사진=' not in sentence and
                '출처:' not in sentence and
                '제공=' not in sentence and
                '이미지=' not in sentence and
                '자료사진' not in sentence and
                '게티이미지' not in sentence and
                'AFP' not in sentence and
                '로이터' not in sentence and
                '닫기' not in sentence and
                '제보는' not in sentence and
                '카카오톡' not in sentence and
                '뉴스제보' not in sentence and
                '독자제보' not in sentence and
                '시청자제보' not in sentence and
                '취재요청' not in sentence and
                '홈페이지' not in sentence and
                '바로가기' not in sentence and
                '로그인' not in sentence and
                '회원가입' not in sentence and
                '.kr' not in sentence and
                '.com' not in sentence):
                sentences.append(sentence)
        
        if len(sentences) == 0:
            # fallback: 마침표로만 분리
            sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 15]
        
        if len(sentences) == 0:
            return "문장을 분리할 수 없습니다."
        
        # 한국어 단어 빈도 계산 (개선된 버전)
        word_freq = {}
        all_text = ' '.join(sentences)
        
        # 한국어 단어 추출 (2글자 이상)
        korean_words = re.findall(r'[가-힣]{2,}', all_text)
        english_words = re.findall(r'[a-zA-Z]{3,}', all_text)
        numbers = re.findall(r'\d+', all_text)
        
        all_words = korean_words + english_words + numbers
        
        # 불용어 확장 (앱/광고 관련 단어 추가)
        stop_words = {
            '이것', '그것', '저것', '이런', '그런', '저런', '이렇게', '그렇게', '저렇게',
            '때문', '경우', '때문에', '하지만', '그러나', '그런데', '또한', '그리고',
            '이다', '있다', '없다', '한다', '된다', '이며', '이고', '에서', '에게',
            '기자', '뉴스', '기사', '보도', '발표', '관련', '대해', '한국', '우리나라',
            '오늘', '어제', '내일', '올해', '지난해', '올해', '내년', '지난', '다음',
            '현재', '최근', '앞으로', '향후', '이후', '이전', '당시', '지금',
            # 앱/광고 관련 불용어 추가
            'jebo23', '라인', '앱에서', '친구', '추가', '좋아요', '응원해요', '후속', '원해요',
            'ADVERTISEMENT', '광고', 'AD', '공유', '공유하기', '구독', '알림', '팔로우',
            '다운로드', '모바일', '페이스북', '트위터', '카카오톡', '네이버', '더보기',
            'yna', 'krc', 'co', 'kr'
        }
        
        for word in all_words:
            if len(word) >= 2 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 문장별 중요도 점수 계산
        sentence_scores = {}
        for sentence in sentences:
            # 문장에서 단어 추출
            sentence_korean = re.findall(r'[가-힣]{2,}', sentence)
            sentence_english = re.findall(r'[a-zA-Z]{3,}', sentence)
            sentence_numbers = re.findall(r'\d+', sentence)
            sentence_words = sentence_korean + sentence_english + sentence_numbers
            
            # 기본 점수 계산
            score = sum(word_freq.get(word, 0) for word in sentence_words)
            
            # 문장 위치 보정 (앞쪽 문장에 더 높은 점수)
            position_weight = 1.0
            sentence_index = sentences.index(sentence)
            if sentence_index < len(sentences) * 0.3:  # 앞쪽 30%
                position_weight = 1.3
            elif sentence_index > len(sentences) * 0.7:  # 뒤쪽 30%
                position_weight = 0.8
            
            # 문장 길이 보정
            length_weight = 1.0
            if 30 <= len(sentence) <= 150:  # 적절한 길이
                length_weight = 1.2
            elif len(sentence) < 20 or len(sentence) > 200:  # 너무 짧거나 김
                length_weight = 0.7
            
            sentence_scores[sentence] = score * position_weight * length_weight
        
        # 상위 문장들 선택
        if len(sentence_scores) == 0:
            return "점수를 계산할 수 없습니다."
        
        top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)
        summary_sentences = [sentence for sentence, score in top_sentences[:max_sentences]]
        
        # 원래 순서대로 정렬 (시간 순서 유지)
        final_sentences = []
        for sentence in sentences:
            if sentence in summary_sentences:
                final_sentences.append(sentence)
                if len(final_sentences) >= max_sentences:
                    break
        
        result = '. '.join(final_sentences)
        if not result.endswith('.'):
            result += '.'
        
        return result if result != '.' else "요약을 생성할 수 없습니다."
    
    def summarize_text(self, text, sentences_count=3):
        """한국어 최적화된 텍스트 요약"""
        try:
            if not text or len(text.strip()) < 50:
                return "요약할 내용이 부족합니다."
            
            # 텍스트 전처리 (한국어 최적화)
            text = re.sub(r'\s+', ' ', text)  # 여러 공백을 하나로
            text = text.strip()
            
            # 기자 정보, 이메일, URL 등 제거 (강화된 버전)
            text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', text)  # 이메일 제거
            text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)  # URL 제거
            text = re.sub(r'[가-힣]+\s*기자', '', text)  # 기자 이름 제거
            text = re.sub(r'【.*?】', '', text)  # 【】 괄호 내용 제거
            text = re.sub(r'\[.*?\]', '', text)  # [] 괄호 내용 제거
            
            # 앱 및 광고 관련 텍스트 제거 (요약 전처리)
            text = re.sub(r'jebo23.*?친구\s*추가.*?@.*?\..*?[가-힣]*', '', text)
            text = re.sub(r'라인\s*앱에서.*?친구\s*추가', '', text)
            text = re.sub(r'좋아요\d+응원해요\d+후속\s*원해요\d+', '', text)
            text = re.sub(r'ADVERTISEMENT', '', text)
            text = re.sub(r'광고', '', text)
            text = re.sub(r'AD', '', text)
            
            # 소셜미디어 및 공유 관련 텍스트 제거
            text = re.sub(r'페이스북.*?공유', '', text)
            text = re.sub(r'트위터.*?공유', '', text)
            text = re.sub(r'카카오톡.*?공유', '', text)
            text = re.sub(r'네이버.*?공유', '', text)
            text = re.sub(r'공유하기', '', text)
            
            # 구독/알림/팔로우 관련 텍스트 제거
            text = re.sub(r'구독.*?알림', '', text)
            text = re.sub(r'팔로우.*?하기', '', text)
            text = re.sub(r'더\s*많은.*?뉴스', '', text)
            text = re.sub(r'뉴스\s*더보기', '', text)
            
            # 앱 다운로드 관련 텍스트 제거
            text = re.sub(r'앱\s*다운로드', '', text)
            text = re.sub(r'모바일.*?앱', '', text)
            
            # 사진/이미지 출처 관련 텍스트 제거 (요약 전처리)
            text = re.sub(r'사진\s*=\s*[^\n.]*', '', text)
            text = re.sub(r'출처\s*:\s*[^\n.]*', '', text)
            text = re.sub(r'제공\s*=\s*[^\n.]*', '', text)
            text = re.sub(r'이미지\s*=\s*[^\n.]*', '', text)
            text = re.sub(r'사진제공\s*[^\n.]*', '', text)
            text = re.sub(r'자료사진\s*[^\n.]*', '', text)
            text = re.sub(r'연합뉴스\s*자료사진', '', text)
            text = re.sub(r'뉴시스\s*자료사진', '', text)
            text = re.sub(r'게티이미지\s*뱅크', '', text)
            text = re.sub(r'AFP\s*연합뉴스', '', text)
            text = re.sub(r'로이터\s*연합뉴스', '', text)
            text = re.sub(r'EPA\s*연합뉴스', '', text)
            text = re.sub(r'AP\s*연합뉴스', '', text)
            text = re.sub(r'사진\s*출처', '', text)
            text = re.sub(r'이미지\s*출처', '', text)
            
            # 웹사이트 UI 및 제보 관련 텍스트 제거 (요약 전처리)
            text = re.sub(r'닫기', '', text)
            text = re.sub(r'제보는.*?카카오톡', '', text)
            text = re.sub(r'제보.*?접수', '', text)
            text = re.sub(r'뉴스\s*제보', '', text)
            text = re.sub(r'독자\s*제보', '', text)
            text = re.sub(r'시청자\s*제보', '', text)
            text = re.sub(r'취재\s*요청', '', text)
            text = re.sub(r'문의.*?연락처', '', text)
            text = re.sub(r'홈페이지.*?바로가기', '', text)
            text = re.sub(r'모바일.*?버전', '', text)
            text = re.sub(r'PC.*?버전', '', text)
            text = re.sub(r'전체.*?메뉴', '', text)
            text = re.sub(r'메뉴.*?닫기', '', text)
            text = re.sub(r'로그인.*?회원가입', '', text)
            text = re.sub(r'회원.*?서비스', '', text)
            text = re.sub(r'이용약관.*?개인정보', '', text)
            text = re.sub(r'개인정보.*?처리방침', '', text)
            text = re.sub(r'저작권.*?정책', '', text)
            text = re.sub(r'청소년.*?보호정책', '', text)
            
            # 도메인 및 기술적 텍스트 제거
            text = re.sub(r'\.kr\b', '', text)
            text = re.sub(r'\.co\.kr\b', '', text)
            text = re.sub(r'\.com\b', '', text)
            text = re.sub(r'www\.', '', text)
            text = re.sub(r'http[s]?://', '', text)
            
            # 연속된 공백과 특수문자 정리
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'[^\w\s가-힣.,!?]', ' ', text)  # 특수문자 제거 (한글, 영문, 숫자, 기본 문장부호만 유지)
            text = text.strip()
            
            # Sumy 시도 (한국어 설정 개선)
            if self.use_sumy:
                try:
                    from sumy.parsers.plaintext import PlaintextParser
                    from sumy.nlp.tokenizers import Tokenizer
                    
                    # 한국어 토크나이저 명시적 설정
                    parser = PlaintextParser.from_string(text, Tokenizer('korean'))
                    summary_sentences = self.summarizer(parser.document, sentences_count)
                    
                    summary = ' '.join([str(sentence).strip() for sentence in summary_sentences])
                    
                    # Sumy 결과 검증
                    if summary and len(summary.strip()) > 20 and '요약' not in summary:
                        return summary.strip()
                    else:
                        return self.simple_summarize(text, sentences_count)
                        
                except Exception as e:
                    # Sumy 실패 시 자체 요약 사용
                    return self.simple_summarize(text, sentences_count)
            else:
                return self.simple_summarize(text, sentences_count)
                
        except Exception as e:
            return f"요약 생성 중 오류 발생: {str(e)}"
    
    def extract_keywords(self, text, top_k=5):
        """간단한 키워드 추출 (개선된 버전)"""
        try:
            if not text:
                return []
            
            # 한글, 영문, 숫자만 추출
            words = re.findall(r'[가-힣a-zA-Z0-9]+', text)
            
            # 불용어 제거 (앱/광고 관련 단어 추가)
            stop_words = {
                '이', '그', '저', '것', '수', '등', '및', '의', '를', '을', '가', '이', '은', '는', 
                '에', '에서', '으로', '로', '와', '과', '하고', '그리고', '또는', '하지만', 
                '그러나', '따라서', '위해', '통해', '대한', '위한', '있는', '없는', '있다', 
                '없다', '이다', '아니다', '한다', '된다', '것이', '것은', '것을',
                '기자', '뉴스', '기사', '보도', '발표', '관련', '대해', '에서', '한국',
                '오늘', '어제', '내일', '올해', '지난', '앞으로',
                # 앱/광고 관련 불용어 추가
                'jebo23', '라인', '앱에서', '친구', '추가', '좋아요', '응원해요', '후속', '원해요',
                'ADVERTISEMENT', '광고', 'AD', '공유', '공유하기', '구독', '알림', '팔로우',
                '다운로드', '모바일', '페이스북', '트위터', '카카오톡', '네이버', '더보기',
                'yna', 'krc', 'co', 'kr', '문화', '연예',
                # 사진/이미지 출처 관련 불용어 추가
                '사진', '출처', '제공', '이미지', '자료사진', '사진제공', '이미지출처', '사진출처',
                '게티이미지', '뱅크', 'AFP', '로이터', '뉴시스', 'EPA', 'AP',
                # 웹사이트 UI 및 제보 관련 불용어 추가
                '닫기', '제보는', '제보', '뉴스제보', '독자제보', '시청자제보', '취재요청', '취재',
                '홈페이지', '바로가기', '로그인', '회원가입', '회원', '서비스', '이용약관',
                '개인정보', '처리방침', '저작권', '정책', '청소년', '보호정책', '메뉴', '전체',
                'www', 'http', 'https', 'com', '버전', 'PC', '모바일', '문의', '연락처', '접수'
            }
            
            # 단어 빈도 계산
            word_freq = {}
            for word in words:
                if len(word) >= 2 and word not in stop_words:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # 단어 길이 가중치 적용
            for word in word_freq:
                if len(word) >= 4:
                    word_freq[word] *= 1.5
            
            # 빈도순으로 정렬하여 상위 키워드 반환
            keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:top_k]
            return [word for word, freq in keywords if freq >= 2]
            
        except Exception as e:
            return []

class PDFGenerator:
    """PDF 보고서 생성 클래스 - 사용자 친화적 디자인"""
    
    def __init__(self):
        # 한글 폰트 등록
        try:
            pdfmetrics.registerFont(TTFont('korean', 'C:/Windows/Fonts/malgun.ttf'))
            pdfmetrics.registerFont(TTFont('korean-bold', 'C:/Windows/Fonts/malgunbd.ttf'))
        except:
            try:
                pdfmetrics.registerFont(TTFont('korean', '/System/Library/Fonts/AppleGothic.ttf'))
                pdfmetrics.registerFont(TTFont('korean-bold', '/System/Library/Fonts/AppleGothic.ttf'))
            except:
                try:
                    pdfmetrics.registerFont(TTFont('korean', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'))
                    pdfmetrics.registerFont(TTFont('korean-bold', '/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc'))
                except:
                    pass
        
        self.setup_styles()
    
    def setup_styles(self):
        """모던하고 사용자 친화적인 스타일 설정"""
        self.styles = getSampleStyleSheet()
        
        # 폰트 설정
        try:
            font_name = 'korean'
            bold_font = 'korean-bold'
        except:
            font_name = 'Helvetica'
            bold_font = 'Helvetica-Bold'
        
        # 색상 정의
        self.colors = {
            'primary': colors.Color(0.2, 0.4, 0.8),      # 진한 파란색
            'secondary': colors.Color(0.1, 0.7, 0.9),    # 하늘색
            'accent': colors.Color(0.9, 0.6, 0.1),       # 주황색
            'success': colors.Color(0.2, 0.7, 0.3),      # 초록색
            'text': colors.Color(0.2, 0.2, 0.2),         # 진한 회색
            'light_bg': colors.Color(0.97, 0.98, 1.0),   # 연한 파란 배경
            'header_bg': colors.Color(0.1, 0.3, 0.6),    # 헤더 배경
            'border': colors.Color(0.8, 0.8, 0.8),       # 테두리 색상
        }
        
        # 스타일 이름 목록 (중복 방지용)
        style_names = [
            'MainTitle', 'SectionTitle', 'ArticleTitle', 
            'BodyText', 'MetaInfo', 'Summary', 'Keywords'
        ]
        
        # 기존 커스텀 스타일 제거 (중복 방지)
        for style_name in style_names:
            if style_name in self.styles.byName:
                del self.styles.byName[style_name]
        
        # 메인 제목 스타일
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Title'],
            fontName=bold_font,
            fontSize=24,
            textColor=self.colors['primary'],
            spaceAfter=30,
            alignment=1,  # 가운데 정렬
            borderWidth=2,
            borderColor=self.colors['primary'],
            borderPadding=15,
            backColor=self.colors['light_bg'],
        ))
        
        # 섹션 제목 스타일
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontName=bold_font,
            fontSize=16,
            textColor=colors.white,
            backColor=self.colors['header_bg'],
            spaceBefore=20,
            spaceAfter=15,
            leftIndent=15,
            rightIndent=15,
            borderPadding=10,
            alignment=0,
        ))
        
        # 기사 제목 스타일
        self.styles.add(ParagraphStyle(
            name='ArticleTitle',
            parent=self.styles['Heading3'],
            fontName=bold_font,
            fontSize=14,
            textColor=self.colors['primary'],
            spaceBefore=15,
            spaceAfter=10,
            leftIndent=5,
            backColor=colors.Color(0.95, 0.97, 1.0),
            borderPadding=8,
        ))
        
        # 본문 스타일
        self.styles.add(ParagraphStyle(
            name='BodyText',
            parent=self.styles['Normal'],
            fontName=font_name,
            fontSize=11,
            textColor=self.colors['text'],
            spaceAfter=8,
            leading=16,
            leftIndent=10,
            rightIndent=10,
        ))
        
        # 메타 정보 스타일
        self.styles.add(ParagraphStyle(
            name='MetaInfo',
            parent=self.styles['Normal'],
            fontName=font_name,
            fontSize=10,
            textColor=colors.Color(0.4, 0.4, 0.4),
            spaceAfter=6,
            leftIndent=10,
        ))
        
        # 요약 스타일
        self.styles.add(ParagraphStyle(
            name='Summary',
            parent=self.styles['Normal'],
            fontName=font_name,
            fontSize=11,
            textColor=self.colors['text'],
            spaceAfter=10,
            leading=16,
            leftIndent=15,
            rightIndent=15,
            backColor=colors.Color(0.98, 1.0, 0.98),
            borderPadding=10,
        ))
        
        # 키워드 스타일
        self.styles.add(ParagraphStyle(
            name='Keywords',
            parent=self.styles['Normal'],
            fontName=font_name,
            fontSize=10,
            textColor=self.colors['accent'],
            spaceAfter=8,
            leftIndent=10,
        ))
    
    def create_header_section(self, keywords, articles_count, user_email):
        """헤더 섹션 생성"""
        elements = []
        
        # 메인 제목
        title = Paragraph("📰 대한민국 뉴스 자동화 보고서", self.styles['MainTitle'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # 보고서 정보 테이블
        report_info = [
            ['🔍 검색 키워드', ', '.join(keywords)],
            ['📊 수집된 기사', f'{articles_count}건'],
            ['📅 생성 일시', datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')],
            ['👤 요청자', user_email],
            ['🏢 언론사', '매일경제, 연합뉴스, SBS, JTBC (총 25개 RSS)']
        ]
        
        info_table = Table(report_info, colWidths=[1.5*inch, 4.5*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), self.colors['light_bg']),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.colors['text']),
            ('FONTNAME', (0, 0), (0, -1), 'korean-bold'),
            ('FONTNAME', (1, 0), (1, -1), 'korean'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, self.colors['border']),
            ('LINEBELOW', (0, 0), (-1, 0), 2, self.colors['primary']),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 30))
        
        return elements
    
    def create_article_section(self, article, index):
        """개별 기사 섹션 생성"""
        elements = []
        
        # 기사 번호와 제목
        title_text = f"{index}. {article['title']}"
        article_title = Paragraph(title_text, self.styles['ArticleTitle'])
        elements.append(article_title)
        elements.append(Spacer(1, 10))
        
        # 기사 메타 정보
        meta_data = [
            ['🔗 URL', article['link'][:80] + '...' if len(article['link']) > 80 else article['link']],
            ['📅 발행일', article.get('published', 'N/A')],
            ['📂 카테고리', article.get('category', 'N/A')],
        ]
        
        meta_table = Table(meta_data, colWidths=[1*inch, 5*inch])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.colors['text']),
            ('FONTNAME', (0, 0), (0, -1), 'korean-bold'),
            ('FONTNAME', (1, 0), (1, -1), 'korean'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, self.colors['border']),
        ]))
        
        elements.append(meta_table)
        elements.append(Spacer(1, 10))
        
        # 키워드 섹션
        if article.get('keywords'):
            keywords_text = f"🏷️ 주요 키워드: {', '.join(article['keywords'][:8])}"
            keywords_para = Paragraph(keywords_text, self.styles['Keywords'])
            elements.append(keywords_para)
            elements.append(Spacer(1, 8))
        
        # 요약 섹션
        summary_text = article.get('summary', '요약 정보가 없습니다.')
        if '요약을 생성할 수 없습니다' in summary_text or '오류' in summary_text:
            summary_formatted = f"⚠️ {summary_text}"
        else:
            summary_formatted = f"📝 {summary_text}"
        
        summary_para = Paragraph(summary_formatted, self.styles['Summary'])
        elements.append(summary_para)
        elements.append(Spacer(1, 20))
        
        # 구분선
        if index < len(self.articles_data):  # 마지막 기사가 아닌 경우
            line_data = [[''] * 6]
            line_table = Table(line_data, colWidths=[6*inch])
            line_table.setStyle(TableStyle([
                ('LINEABOVE', (0, 0), (-1, -1), 1, self.colors['border']),
            ]))
            elements.append(line_table)
            elements.append(Spacer(1, 15))
        
        return elements
    
    def create_footer_section(self):
        """푸터 섹션 생성"""
        elements = []
        
        elements.append(Spacer(1, 30))
        
        footer_data = [
            ['생성 시스템: AI 뉴스 자동화 시스템 v2.0', f'생성 시간: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}']
        ]
        
        footer_table = Table(footer_data, colWidths=[3*inch, 3*inch])
        footer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.Color(0.5, 0.5, 0.5)),
            ('FONTNAME', (0, 0), (-1, -1), 'korean'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(footer_table)
        
        return elements
    
    def generate_report(self, articles_data, keywords, user_email):
        """사용자 친화적인 PDF 보고서 생성"""
        self.articles_data = articles_data  # 클래스 변수로 저장
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        story = []
        
        # 1. 헤더 섹션
        header_elements = self.create_header_section(keywords, len(articles_data), user_email)
        story.extend(header_elements)
        
        # 2. 기사 목록 섹션 제목
        section_title = Paragraph("📄 수집된 뉴스 기사 목록", self.styles['SectionTitle'])
        story.append(section_title)
        story.append(Spacer(1, 15))
        
        # 3. 각 기사 섹션
        for i, article in enumerate(articles_data, 1):
            article_elements = self.create_article_section(article, i)
            story.extend(article_elements)
            
            # 페이지 나누기 (4개 기사마다)
            if i % 4 == 0 and i < len(articles_data):
                story.append(Spacer(1, 30))
        
        # 4. 푸터 섹션
        footer_elements = self.create_footer_section()
        story.extend(footer_elements)
        
        # PDF 생성
        doc.build(story)
        buffer.seek(0)
        return buffer

class EmailSender:
    """이메일 발송 클래스"""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.sender_email = os.getenv('GMAIL_EMAIL')
        self.sender_password = os.getenv('GMAIL_APP_PASSWORD')
    
    def is_configured(self):
        """이메일 설정이 완료되었는지 확인"""
        return bool(self.sender_email and self.sender_password)
    
    def send_report_email(self, recipient_email, pdf_buffer, keywords, sender_email=None, sender_password=None):
        """PDF 보고서를 이메일로 발송"""
        try:
            email = sender_email or self.sender_email
            password = sender_password or self.sender_password
            
            if not email or not password:
                return False, "이메일 설정이 완료되지 않았습니다."
            
            # 이메일 메시지 생성
            msg = MIMEMultipart()
            msg['From'] = email
            msg['To'] = recipient_email
            msg['Subject'] = f"뉴스 요약 보고서 - {', '.join(keywords)} ({datetime.now().strftime('%Y-%m-%d')})"
            
            # 이메일 본문
            body = f"""안녕하세요,

요청하신 뉴스 요약 보고서를 첨부파일로 보내드립니다.

[보고서 정보]
- 검색 키워드: {', '.join(keywords)}
- 생성 일시: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}
- 발송자: {email}

첨부파일을 확인해주세요.

감사합니다.

---
뉴스 자동화 시스템"""
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # PDF 첨부파일 추가
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(pdf_buffer.read())
            encoders.encode_base64(attachment)
            
            filename = f"news_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename={filename}'
            )
            msg.attach(attachment)
            
            # SMTP 서버 연결 및 발송
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(email, password)
            text = msg.as_string()
            server.sendmail(email, recipient_email, text)
            server.quit()
            
            return True, f"이메일이 성공적으로 발송되었습니다! ({email} -> {recipient_email})"
            
        except Exception as e:
            return False, f"이메일 발송 중 오류 발생: {str(e)}"

def main():
    """메인 Streamlit 앱"""
    st.set_page_config(
        page_title="뉴스 자동화 시스템",
        page_icon="📰",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 커스텀 CSS 추가 (UI 개선)
    st.markdown("""
    <style>
    /* 텍스트 입력창 스타일 개선 */
    .stTextInput > div > div > input {
        height: 3rem !important;
        padding: 0.75rem 1rem !important;
        display: flex !important;
        align-items: center !important;
        vertical-align: middle !important;
        line-height: 1.5rem !important;
        font-size: 1rem !important;
    }
    
    /* 텍스트 입력창 라벨 스타일 */
    .stTextInput > label {
        font-size: 1rem !important;
        font-weight: 600 !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* 버튼 스타일 개선 */
    .stButton > button {
        height: 3rem !important;
        padding: 0.75rem 1rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        border-radius: 0.5rem !important;
        margin-top: 0rem !important;
    }
    
    /* 버튼 컨테이너 정렬 */
    .stButton {
        display: flex !important;
        align-items: flex-end !important;
        height: 100% !important;
    }
    
    /* 컬럼 높이 통일 */
    .stColumn {
        display: flex !important;
        flex-direction: column !important;
    }
    
    /* 컬럼 간격 조정 */
    .block-container {
        padding-top: 1rem;
    }
    
    /* 메트릭 카드 스타일 개선 */
    .metric-container {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    
    /* 헤더 스타일 개선 */
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* 입력창과 버튼의 수직 정렬을 위한 추가 스타일 */
    .stTextInput {
        margin-bottom: 0 !important;
    }
    
    /* 라벨과 입력창 사이 간격 조정 */
    .stTextInput > div {
        gap: 0.5rem !important;
    }
    
    /* Primary 버튼 스타일 강화 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #ff6b6b 0%, #ee5a52 100%) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(90deg, #ff5252 0%, #d32f2f 100%) !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2) !important;
        transform: translateY(-1px) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 헤더 (스타일 개선)
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0;">📰 대한민국 뉴스 자동화 시스템</h1>
        <p style="margin:0.5rem 0 0 0; opacity:0.9;">국내 대표 언론사들을 한번에 보실 수 있는 스마트한 뉴스 수집 플랫폼입니다 - 요약 및 PDF 보고서 생성</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 사이드바 설정 (RSS 선택 기능 제거)
    st.sidebar.header("⚙️ 시스템 설정")
    
    # 고급 설정만 유지
    with st.sidebar.expander("🔧 고급 설정", expanded=False):
        summary_sentences = st.slider("📝 요약 문장 수", 1, 5, 3)
        keyword_count = st.slider("🏷️ 키워드 추출 수", 3, 15, 8)
        
        st.write("**🎯 요약 방식:**")
        summary_method = st.radio(
            "방식 선택",
            ["한국어 최적화", "Sumy 라이브러리", "간단 요약"],
            index=0,
            help="한국어 최적화: 한국어 뉴스에 특화된 요약 방식"
        )
    
    # 이메일 설정 상태 표시
    email_sender = EmailSender()
    if email_sender.is_configured():
        st.sidebar.success("✅ 이메일 설정 완료")
        st.sidebar.info(f"📧 발송자: {email_sender.sender_email}")
    else:
        st.sidebar.warning("⚠️ 이메일 설정 필요")
    
    # 세션 상태 초기화
    if 'articles_data' not in st.session_state:
        st.session_state.articles_data = []
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    
    # 1단계: 키워드 입력
    st.header("1️⃣ 키워드 입력 및 뉴스 수집")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        keywords_input = st.text_input(
            "🔍 검색할 키워드를 입력하세요 (쉼표로 구분)",
            placeholder="예: AI, 인공지능, 머신러닝, 딥러닝",
            help="여러 키워드는 쉼표(,)로 구분해서 입력하세요."
        )
    
    with col2:
        # 라벨 높이와 동일한 공간 확보
        st.markdown('<div style="height: 1.5rem; margin-bottom: 0.5rem;"></div>', unsafe_allow_html=True)
        search_button = st.button("🚀 뉴스 수집 시작", type="primary", use_container_width=True)
    
    # SBS 헤드라인 뉴스 미리보기 (첫 화면 활성화)
    if not st.session_state.processing_complete:
        st.markdown("---")
        st.subheader("📺 SBS 헤드라인 뉴스 (실시간)")
        
        # SBS 헤드라인 뉴스 가져오기
        @st.cache_data(ttl=300)  # 5분 캐시
        def get_sbs_headlines():
            try:
                collector = NewsCollector()
                sbs_url = "https://news.sbs.co.kr/news/headlineRssFeed.do?plink=RSSREADER"
                articles = collector.get_rss_feeds(sbs_url, "SBS_헤드라인")
                return articles[:10]  # 상위 10개만
            except Exception as e:
                st.error(f"SBS 뉴스 로딩 중 오류: {str(e)}")
                return []
        
        sbs_headlines = get_sbs_headlines()
        
        if sbs_headlines:
            # 뉴스 카드 스타일로 표시
            for i, article in enumerate(sbs_headlines, 1):
                with st.container():
                    col1, col2 = st.columns([1, 20])
                    
                    with col1:
                        st.markdown(f"**{i}**")
                    
                    with col2:
                        # 제목을 클릭 가능한 링크로 표시
                        st.markdown(f"**[{article['title']}]({article['link']})**")
                        
                        # 발행일과 간단한 설명
                        if article.get('published'):
                            st.caption(f"📅 {article['published']}")
                        
                        if article.get('description'):
                            # 설명이 너무 길면 자르기
                            desc = article['description'][:150] + "..." if len(article['description']) > 150 else article['description']
                            st.markdown(f"<small style='color: #666;'>{desc}</small>", unsafe_allow_html=True)
                        
                        st.markdown("---")
        else:
            st.info("SBS 헤드라인 뉴스를 불러오는 중입니다...")
        
        st.markdown("💡 **위 뉴스들은 실시간 SBS 헤드라인입니다. 키워드를 입력하여 맞춤형 뉴스 검색을 시작해보세요!**")
    
    # 뉴스 수집 실행
    if search_button and keywords_input:
        keywords = [kw.strip() for kw in keywords_input.split(',') if kw.strip()]
        
        if keywords:
            # 간단한 로딩 메시지만 표시
            with st.spinner("🔄 뉴스 기사를 수집하고 분석하고 있습니다..."):
                try:
                    collector = NewsCollector()
                    
                    # 모든 RSS 자동 수집 (상세 진행률 없이)
                    articles = collector.collect_news_with_content(keywords)
                    
                    if articles:
                        processor = TextProcessor()
                        processed_articles = []
                        
                        # AI 분석 진행률 (간단하게)
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        status_text.text(f"AI 분석 중... (0/{len(articles)})")
                        
                        for i, article in enumerate(articles):
                            progress_bar.progress((i + 1) / len(articles))
                            status_text.text(f"AI 분석 중... ({i+1}/{len(articles)})")
                            
                            # 요약 방식 선택에 따른 처리
                            if summary_method == "한국어 최적화":
                                summary = processor.simple_summarize(article['content'], summary_sentences)
                            else:
                                summary = processor.summarize_text(article['content'], summary_sentences)
                            
                            extracted_keywords = processor.extract_keywords(article['content'], keyword_count)
                            
                            article['summary'] = summary
                            article['keywords'] = extracted_keywords
                            processed_articles.append(article)
                        
                        # 진행률 바 제거
                        progress_bar.empty()
                        status_text.empty()
                        
                        st.session_state.articles_data = processed_articles
                        st.session_state.processing_complete = True
                        st.session_state.search_keywords = keywords
                        
                        st.balloons()
                        
                        # 최종 결과만 간단히 표시
                        category_summary = {}
                        for article in processed_articles:
                            cat = article.get('category', '기타')
                            category_summary[cat] = category_summary.get(cat, 0) + 1
                        
                        st.success(f"🎉 수집 완료! {len(processed_articles)}개의 기사를 성공적으로 수집하고 분석했습니다!")
                        
                        # 카테고리별 간단한 통계 (한 줄로)
                        category_text = ", ".join([f"{cat}({count})" for cat, count in category_summary.items()])
                        st.info(f"📊 카테고리별 수집: {category_text}")
                        
                    else:
                        st.warning("😅 해당 키워드로 검색된 기사가 없습니다.")
                        
                except Exception as e:
                    st.error(f"❌ 오류 발생: {str(e)}")
        else:
            st.warning("⚠️ 키워드를 입력해주세요.")
    
    # 2단계: 결과 표시
    if st.session_state.processing_complete and st.session_state.articles_data:
        st.header("2️⃣ 수집 결과 분석")
        
        # 통계 정보 표시
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📰 수집된 기사", len(st.session_state.articles_data))
        
        with col2:
            successful_summaries = sum(1 for article in st.session_state.articles_data 
                                     if '요약을 생성할 수 없습니다' not in article.get('summary', ''))
            success_rate = (successful_summaries / len(st.session_state.articles_data)) * 100
            st.metric("✅ 요약 성공률", f"{success_rate:.1f}%")
        
        with col3:
            avg_keywords = sum(len(article.get('keywords', [])) for article in st.session_state.articles_data) / len(st.session_state.articles_data)
            st.metric("🏷️ 평균 키워드", f"{avg_keywords:.1f}개")
        
        with col4:
            st.metric("🔍 검색 키워드", len(st.session_state.search_keywords))
        
        # 키워드 클라우드
        with st.expander("🏷️ 주요 키워드 분석", expanded=False):
            all_keywords = []
            for article in st.session_state.articles_data:
                all_keywords.extend(article.get('keywords', []))
            
            if all_keywords:
                keyword_freq = Counter(all_keywords)
                top_keywords = keyword_freq.most_common(15)
                
                keyword_html = ""
                colors_list = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FCEA2B', '#FF9F43', '#EE5A52', '#0FB9B1', '#A29BFE', '#FD79A8']
                
                for i, (keyword, freq) in enumerate(top_keywords):
                    color = colors_list[i % len(colors_list)]
                    keyword_html += f'<span style="background-color: {color}; color: white; padding: 5px 10px; margin: 3px; border-radius: 15px; font-size: 12px; display: inline-block;">{keyword} ({freq})</span>'
                
                st.markdown(keyword_html, unsafe_allow_html=True)
            else:
                st.info("키워드가 추출되지 않았습니다.")
        
        # 기사 목록 표시
        st.subheader("📄 수집된 기사 목록")
        
        # 카테고리별 필터링 옵션만 유지 (뱃지 표시 옵션 제거)
        if st.session_state.articles_data:
            categories_in_results = list(set(article.get('category', '기타') for article in st.session_state.articles_data))
            
            selected_filter_category = st.selectbox(
                "카테고리별 필터링",
                options=["전체 보기"] + categories_in_results,
                index=0
            )
        
        # 필터링된 기사 목록
        filtered_display_articles = st.session_state.articles_data
        if selected_filter_category != "전체 보기":
            filtered_display_articles = [
                article for article in st.session_state.articles_data 
                if article.get('category', '기타') == selected_filter_category
            ]
        
        # 기사 목록 표시 (뱃지 없이 깔끔하게)
        for i, article in enumerate(filtered_display_articles, 1):
            with st.expander(f"📰 {i}. {article['title']}", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**🔗 링크:** {article['link']}")
                    st.markdown(f"**📅 발행일:** {article.get('published', 'N/A')}")
                    st.markdown(f"**📂 카테고리:** {article.get('category', '기타')}")
                    
                    # 요약 품질에 따른 색상 표시
                    summary = article['summary']
                    if '요약을 생성할 수 없습니다' in summary or '오류' in summary:
                        st.markdown(f"**📝 요약:** <span style='color: orange;'>{summary}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**📝 요약:** <span style='color: green;'>{summary}</span>", unsafe_allow_html=True)
                
                with col2:
                    st.markdown("**🏷️ 키워드:**")
                    for keyword in article['keywords'][:6]:
                        st.markdown(f"• {keyword}")
        
        # 3단계: PDF 생성 및 이메일 발송
        st.header("3️⃣ 보고서 생성 및 발송")
        
        # 레이아웃 개선: 이메일 입력과 버튼을 같은 행에 배치
        col1, col2, col3 = st.columns([2, 3, 2])
        
        with col1:
            # CSV 다운로드
            if st.button("📊 CSV 다운로드", use_container_width=True):
                try:
                    df_data = []
                    for i, article in enumerate(st.session_state.articles_data, 1):
                        df_data.append({
                            '번호': i,
                            '제목': article['title'],
                            'URL': article['link'],
                            '발행일': article.get('published', ''),
                            '카테고리': article.get('category', ''),
                            '요약': article.get('summary', ''),
                            '키워드': ', '.join(article.get('keywords', [])),
                            '수집시간': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                    
                    df = pd.DataFrame(df_data)
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    
                    st.download_button(
                        label="💾 CSV 파일 다운로드",
                        data=csv,
                        file_name=f"news_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    st.success("✅ CSV 파일이 준비되었습니다!")
                    
                except Exception as e:
                    st.error(f"❌ CSV 생성 오류: {str(e)}")
        
        with col2:
            recipient_email = st.text_input(
                "📧 받을 이메일 주소",
                placeholder="example@gmail.com",
                help="PDF 보고서를 받을 이메일 주소를 입력하세요"
            )
        
        with col3:
            # 라벨 높이와 동일한 공간 확보
            st.markdown('<div style="height: 1.5rem; margin-bottom: 0.5rem;"></div>', unsafe_allow_html=True)
            generate_pdf_button = st.button("📄 PDF 생성 및 발송", type="primary", use_container_width=True)
        
        # 이메일 설정
        email_sender = EmailSender()
        manual_email_input = not email_sender.is_configured()
        
        with st.expander("📧 이메일 발송 설정", expanded=manual_email_input):
            if email_sender.is_configured():
                st.success(f"✅ 현재 설정: {email_sender.sender_email}")
                use_env_email = st.checkbox("환경변수 설정 사용", value=True)
            else:
                use_env_email = False
                st.warning("환경변수에서 이메일 설정을 찾을 수 없습니다.")
            
            if not use_env_email or not email_sender.is_configured():
                st.markdown("**📤 수동 이메일 설정:**")
                manual_sender_email = st.text_input(
                    "발송자 Gmail 주소", 
                    value=email_sender.sender_email or "",
                    placeholder="your_email@gmail.com"
                )
                manual_sender_password = st.text_input(
                    "Gmail 앱 비밀번호", 
                    type="password",
                    help="Gmail 2단계 인증 후 생성한 앱 비밀번호를 입력하세요"
                )
            else:
                manual_sender_email = None
                manual_sender_password = None
        
        # PDF 생성 및 발송
        if generate_pdf_button and recipient_email:
            try:
                with st.spinner("📄 PDF 보고서를 생성하고 있습니다..."):
                    pdf_generator = PDFGenerator()
                    pdf_buffer = pdf_generator.generate_report(
                        st.session_state.articles_data,
                        st.session_state.search_keywords,
                        recipient_email
                    )
                    
                    pdf_filename = f"news_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            label="📄 PDF 다운로드",
                            data=pdf_buffer.getvalue(),
                            file_name=pdf_filename,
                            mime="application/pdf",
                            use_container_width=True
                        )
                    
                    with col2:
                        st.success("✅ PDF 생성 완료!")
                    
                    # 이메일 발송
                    with st.spinner("📧 이메일을 발송하고 있습니다..."):
                        pdf_buffer.seek(0)
                        
                        success, message = email_sender.send_report_email(
                            recipient_email,
                            pdf_buffer,
                            st.session_state.search_keywords,
                            manual_sender_email,
                            manual_sender_password
                        )
                        
                        if success:
                            st.success(f"🎉 {message}")
                            st.balloons()
                        else:
                            st.error(f"❌ {message}")
                    
            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {str(e)}")
        
        elif generate_pdf_button and not recipient_email:
            st.warning("⚠️ 받을 이메일 주소를 입력해주세요.")
    
    # 사이드바 추가 정보
    st.sidebar.markdown("---")
    st.sidebar.header("📊 수집 통계")
    
    if st.session_state.processing_complete:
        st.sidebar.metric("수집된 기사", len(st.session_state.articles_data))
        st.sidebar.metric("검색 키워드", len(st.session_state.get('search_keywords', [])))
        st.sidebar.metric("RSS 피드 수", "25개 (매경+연합+SBS+JTBC)")
        
        # 카테고리별 통계
        if 'articles_data' in st.session_state and st.session_state.articles_data:
            st.sidebar.write("**언론사별 기사 수:**")
            media_counts = {}
            for article in st.session_state.articles_data:
                cat = article.get('category', '기타')
                # 언론사별로 그룹화
                if '매경_' in cat:
                    media = '매일경제'
                elif '연합' in cat:
                    media = '연합뉴스'
                elif 'SBS' in cat:
                    media = 'SBS'
                elif 'JTBC' in cat:
                    media = 'JTBC'
                else:
                    media = '기타'
                
                media_counts[media] = media_counts.get(media, 0) + 1
            
            for media, count in sorted(media_counts.items()):
                st.sidebar.write(f"• {media}: {count}개")

if __name__ == "__main__":
    main()