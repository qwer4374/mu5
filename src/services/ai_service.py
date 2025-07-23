#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI Service
==========

Advanced AI service providing intelligent features like content analysis,
smart recommendations, automated responses, and predictive analytics.
"""

import logging
import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
import openai

class AIService:
    """Advanced AI service with multiple intelligent features."""
    
    def __init__(self, config):
        """Initialize AI service."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize OpenAI client
        self.openai_client = openai.AsyncOpenAI()
        
        # AI model configurations
        self.models = {
            'content_analysis': 'gpt-3.5-turbo',
            'recommendations': 'gpt-3.5-turbo',
            'chat_response': 'gpt-3.5-turbo',
            'text_generation': 'gpt-3.5-turbo',
            'translation': 'gpt-3.5-turbo'
        }
        
        # Cache for AI responses
        self.response_cache = {}
        self.cache_ttl = 3600  # 1 hour
    
    async def analyze_content(self, content: str, content_type: str = 'text') -> Dict[str, Any]:
        """Analyze content using AI for safety, quality, and categorization."""
        try:
            cache_key = f"content_analysis_{hash(content)}"
            
            # Check cache first
            if cache_key in self.response_cache:
                cached_result = self.response_cache[cache_key]
                if datetime.now().timestamp() - cached_result['timestamp'] < self.cache_ttl:
                    return cached_result['data']
            
            # Prepare analysis prompt
            prompt = f"""
            تحليل المحتوى التالي وتقديم تقرير شامل:

            نوع المحتوى: {content_type}
            المحتوى: {content[:1000]}...

            يرجى تحليل المحتوى من النواحي التالية:
            1. الأمان والملاءمة (هل المحتوى آمن ومناسب؟)
            2. الجودة والمصداقية
            3. التصنيف والفئة
            4. اللغة المستخدمة
            5. المشاعر والنبرة
            6. الكلمات المفتاحية الرئيسية
            7. التوصيات للتحسين

            قدم الإجابة بصيغة JSON مع المفاتيح التالية:
            - safety_score (0-100)
            - quality_score (0-100)
            - category
            - language
            - sentiment
            - keywords
            - recommendations
            - is_appropriate (true/false)
            """
            
            response = await self.openai_client.chat.completions.create(
                model=self.models['content_analysis'],
                messages=[
                    {"role": "system", "content": "أنت محلل محتوى ذكي متخصص في تحليل النصوص العربية والإنجليزية."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse AI response
            ai_response = response.choices[0].message.content
            
            try:
                # Try to parse as JSON
                analysis_result = json.loads(ai_response)
            except json.JSONDecodeError:
                # Fallback to basic analysis
                analysis_result = self._basic_content_analysis(content)
            
            # Add additional analysis
            analysis_result.update({
                'content_length': len(content),
                'word_count': len(content.split()),
                'analysis_timestamp': datetime.now().isoformat(),
                'readability_score': self._calculate_readability(content),
                'spam_indicators': self._detect_spam_indicators(content)
            })
            
            # Cache result
            self.response_cache[cache_key] = {
                'data': analysis_result,
                'timestamp': datetime.now().timestamp()
            }
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error in content analysis: {e}")
            return self._basic_content_analysis(content)
    
    async def generate_smart_response(self, user_message: str, user_context: Dict[str, Any]) -> str:
        """Generate intelligent response based on user message and context."""
        try:
            # Prepare context information
            context_info = f"""
            معلومات المستخدم:
            - الاسم: {user_context.get('first_name', 'غير محدد')}
            - اللغة المفضلة: {user_context.get('language_code', 'ar')}
            - عدد التحميلات: {user_context.get('download_count', 0)}
            - آخر نشاط: {user_context.get('last_activity', 'غير محدد')}
            - مستوى المستخدم: {user_context.get('user_level', 'مبتدئ')}
            """
            
            prompt = f"""
            أنت مساعد ذكي لبوت تحميل الملفات. المستخدم أرسل الرسالة التالية:
            "{user_message}"

            {context_info}

            قدم رداً مفيداً ومناسباً باللغة العربية. يجب أن يكون الرد:
            - ودود ومهذب
            - مفيد وعملي
            - مناسب لمستوى المستخدم
            - يتضمن إرشادات واضحة إذا لزم الأمر
            - لا يزيد عن 200 كلمة
            """
            
            response = await self.openai_client.chat.completions.create(
                model=self.models['chat_response'],
                messages=[
                    {"role": "system", "content": "أنت مساعد ذكي ومفيد لبوت تحميل الملفات، تتحدث باللغة العربية بطريقة ودودة ومهنية."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"Error generating smart response: {e}")
            return "شكراً لرسالتك! كيف يمكنني مساعدتك اليوم؟"
    
    async def generate_personalized_recommendations(self, user_id: int, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate personalized recommendations for the user."""
        try:
            # Analyze user behavior patterns
            download_history = user_data.get('download_history', [])
            preferences = user_data.get('preferences', {})
            activity_patterns = user_data.get('activity_patterns', {})
            
            # Prepare recommendation prompt
            prompt = f"""
            بناءً على بيانات المستخدم التالية، قدم توصيات شخصية مفيدة:

            سجل التحميلات الأخيرة:
            {json.dumps(download_history[-10:], ensure_ascii=False, indent=2)}

            التفضيلات:
            {json.dumps(preferences, ensure_ascii=False, indent=2)}

            أنماط النشاط:
            {json.dumps(activity_patterns, ensure_ascii=False, indent=2)}

            قدم 5 توصيات شخصية في صيغة JSON مع المفاتيح التالية لكل توصية:
            - title: عنوان التوصية
            - description: وصف مفصل
            - action: الإجراء المطلوب
            - priority: الأولوية (high/medium/low)
            - category: الفئة (download/settings/feature/tip)
            """
            
            response = await self.openai_client.chat.completions.create(
                model=self.models['recommendations'],
                messages=[
                    {"role": "system", "content": "أنت خبير في تحليل سلوك المستخدمين وتقديم توصيات شخصية مفيدة."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=800
            )
            
            try:
                recommendations = json.loads(response.choices[0].message.content)
                if isinstance(recommendations, list):
                    return recommendations
                elif isinstance(recommendations, dict) and 'recommendations' in recommendations:
                    return recommendations['recommendations']
            except json.JSONDecodeError:
                pass
            
            # Fallback recommendations
            return self._generate_fallback_recommendations(user_data)
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return self._generate_fallback_recommendations(user_data)
    
    async def analyze_url_safety(self, url: str) -> Dict[str, Any]:
        """Analyze URL for safety and legitimacy."""
        try:
            # Parse URL
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Basic safety checks
            safety_analysis = {
                'url': url,
                'domain': domain,
                'is_https': parsed_url.scheme == 'https',
                'safety_score': 50,  # Default neutral score
                'risk_level': 'medium',
                'warnings': [],
                'recommendations': []
            }
            
            # Check against known safe/unsafe patterns
            safe_domains = ['youtube.com', 'youtu.be', 'drive.google.com', 'dropbox.com', 'mega.nz']
            suspicious_patterns = ['bit.ly', 'tinyurl.com', 'short.link']
            
            if any(safe_domain in domain for safe_domain in safe_domains):
                safety_analysis['safety_score'] = 85
                safety_analysis['risk_level'] = 'low'
            elif any(pattern in domain for pattern in suspicious_patterns):
                safety_analysis['safety_score'] = 30
                safety_analysis['risk_level'] = 'high'
                safety_analysis['warnings'].append('رابط مختصر - قد يخفي الوجهة الحقيقية')
            
            # Check for suspicious patterns in URL
            if re.search(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', domain):
                safety_analysis['warnings'].append('الرابط يستخدم عنوان IP بدلاً من اسم النطاق')
                safety_analysis['safety_score'] -= 20
            
            if len(domain.split('.')) > 4:
                safety_analysis['warnings'].append('نطاق فرعي معقد - قد يكون مشبوهاً')
                safety_analysis['safety_score'] -= 10
            
            # Use AI for additional analysis
            ai_analysis = await self._ai_url_analysis(url)
            safety_analysis.update(ai_analysis)
            
            return safety_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing URL safety: {e}")
            return {
                'url': url,
                'safety_score': 50,
                'risk_level': 'unknown',
                'warnings': ['فشل في تحليل الرابط'],
                'recommendations': ['تحقق من الرابط يدوياً قبل التحميل']
            }
    
    async def _ai_url_analysis(self, url: str) -> Dict[str, Any]:
        """Use AI to analyze URL for additional insights."""
        try:
            prompt = f"""
            حلل الرابط التالي من ناحية الأمان والمصداقية:
            {url}

            قدم تحليلاً يتضمن:
            1. مستوى الأمان (0-100)
            2. مستوى المخاطر (low/medium/high)
            3. التحذيرات المحتملة
            4. التوصيات

            قدم الإجابة بصيغة JSON مع المفاتيح:
            - ai_safety_score
            - ai_risk_assessment
            - ai_warnings (array)
            - ai_recommendations (array)
            """
            
            response = await self.openai_client.chat.completions.create(
                model=self.models['content_analysis'],
                messages=[
                    {"role": "system", "content": "أنت خبير أمن سيبراني متخصص في تحليل الروابط والمواقع."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=400
            )
            
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                return {}
                
        except Exception as e:
            self.logger.error(f"Error in AI URL analysis: {e}")
            return {}
    
    async def generate_download_summary(self, download_data: Dict[str, Any]) -> str:
        """Generate intelligent summary for download completion."""
        try:
            prompt = f"""
            أنشئ ملخصاً ذكياً لعملية التحميل التالية:

            معلومات التحميل:
            - اسم الملف: {download_data.get('filename', 'غير محدد')}
            - حجم الملف: {download_data.get('file_size_mb', 0)} MB
            - نوع الملف: {download_data.get('file_type', 'غير محدد')}
            - مدة التحميل: {download_data.get('duration_seconds', 0)} ثانية
            - حالة التحميل: {download_data.get('status', 'غير محدد')}
            - المصدر: {download_data.get('source_domain', 'غير محدد')}

            أنشئ ملخصاً قصيراً (50-100 كلمة) يتضمن:
            - تأكيد نجاح/فشل التحميل
            - معلومات مفيدة عن الملف
            - نصائح أو توصيات إذا لزم الأمر
            - رسالة ودودة ومشجعة
            """
            
            response = await self.openai_client.chat.completions.create(
                model=self.models['text_generation'],
                messages=[
                    {"role": "system", "content": "أنت مساعد ذكي يقدم ملخصات مفيدة وودودة لعمليات التحميل."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"Error generating download summary: {e}")
            return f"تم تحميل الملف {download_data.get('filename', '')} بنجاح! 🎉"
    
    async def translate_text(self, text: str, target_language: str = 'ar') -> str:
        """Translate text to target language."""
        try:
            if not text.strip():
                return text
            
            # Check if translation is needed
            if target_language == 'ar' and self._is_arabic_text(text):
                return text
            elif target_language == 'en' and self._is_english_text(text):
                return text
            
            language_names = {
                'ar': 'العربية',
                'en': 'الإنجليزية',
                'fr': 'الفرنسية',
                'es': 'الإسبانية',
                'de': 'الألمانية'
            }
            
            target_lang_name = language_names.get(target_language, target_language)
            
            prompt = f"""
            ترجم النص التالي إلى {target_lang_name}:
            
            "{text}"
            
            قدم الترجمة فقط دون أي تعليقات إضافية.
            """
            
            response = await self.openai_client.chat.completions.create(
                model=self.models['translation'],
                messages=[
                    {"role": "system", "content": f"أنت مترجم محترف متخصص في الترجمة إلى {target_lang_name}."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=len(text) * 2
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"Error translating text: {e}")
            return text  # Return original text if translation fails
    
    async def generate_help_content(self, user_query: str, user_level: str = 'beginner') -> str:
        """Generate contextual help content based on user query."""
        try:
            level_descriptions = {
                'beginner': 'مبتدئ يحتاج شرح مفصل وبسيط',
                'intermediate': 'متوسط يفهم الأساسيات',
                'advanced': 'متقدم يحتاج معلومات تقنية'
            }
            
            prompt = f"""
            المستخدم ({level_descriptions.get(user_level, 'مبتدئ')}) يسأل:
            "{user_query}"

            قدم إجابة مفيدة ومناسبة لمستواه تتضمن:
            1. إجابة مباشرة على السؤال
            2. خطوات عملية إذا لزم الأمر
            3. نصائح إضافية مفيدة
            4. أمثلة عملية إذا أمكن

            اجعل الإجابة واضحة ومفيدة ولا تزيد عن 300 كلمة.
            """
            
            response = await self.openai_client.chat.completions.create(
                model=self.models['chat_response'],
                messages=[
                    {"role": "system", "content": "أنت خبير تقني متخصص في مساعدة المستخدمين بطريقة واضحة ومفيدة."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"Error generating help content: {e}")
            return "عذراً، لا يمكنني الإجابة على سؤالك حالياً. يرجى المحاولة لاحقاً أو التواصل مع الدعم الفني."
    
    # Helper methods
    def _basic_content_analysis(self, content: str) -> Dict[str, Any]:
        """Provide basic content analysis without AI."""
        return {
            'safety_score': 70,
            'quality_score': 60,
            'category': 'general',
            'language': 'ar' if self._is_arabic_text(content) else 'en',
            'sentiment': 'neutral',
            'keywords': self._extract_basic_keywords(content),
            'recommendations': ['المحتوى يبدو مناسباً للاستخدام العام'],
            'is_appropriate': True
        }
    
    def _is_arabic_text(self, text: str) -> bool:
        """Check if text is primarily Arabic."""
        arabic_chars = sum(1 for char in text if '\u0600' <= char <= '\u06FF')
        return arabic_chars > len(text) * 0.3
    
    def _is_english_text(self, text: str) -> bool:
        """Check if text is primarily English."""
        english_chars = sum(1 for char in text if char.isalpha() and ord(char) < 128)
        return english_chars > len(text) * 0.5
    
    def _extract_basic_keywords(self, text: str) -> List[str]:
        """Extract basic keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter common words (this would be more sophisticated in practice)
        common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                       'من', 'إلى', 'في', 'على', 'عن', 'مع', 'هذا', 'هذه', 'ذلك', 'التي', 'الذي'}
        keywords = [word for word in set(words) if len(word) > 3 and word not in common_words]
        return keywords[:10]  # Return top 10 keywords
    
    def _calculate_readability(self, text: str) -> float:
        """Calculate basic readability score."""
        if not text:
            return 0
        
        words = len(text.split())
        sentences = len(re.split(r'[.!?]+', text))
        
        if sentences == 0:
            return 50
        
        avg_words_per_sentence = words / sentences
        
        # Simple readability score (higher is more readable)
        if avg_words_per_sentence <= 15:
            return 80
        elif avg_words_per_sentence <= 25:
            return 60
        else:
            return 40
    
    def _detect_spam_indicators(self, text: str) -> List[str]:
        """Detect potential spam indicators in text."""
        indicators = []
        
        # Check for excessive capitalization
        if sum(1 for c in text if c.isupper()) > len(text) * 0.5:
            indicators.append('استخدام مفرط للأحرف الكبيرة')
        
        # Check for excessive punctuation
        if sum(1 for c in text if c in '!?') > len(text) * 0.1:
            indicators.append('استخدام مفرط لعلامات التعجب والاستفهام')
        
        # Check for suspicious patterns
        if re.search(r'(free|مجاني|مجانا).*(download|تحميل)', text.lower()):
            indicators.append('محتوى ترويجي محتمل')
        
        return indicators
    
    def _generate_fallback_recommendations(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fallback recommendations when AI fails."""
        return [
            {
                'title': 'تحسين تجربة التحميل',
                'description': 'جرب استخدام الميزات المتقدمة للتحميل للحصول على أداء أفضل',
                'action': 'explore_advanced_features',
                'priority': 'medium',
                'category': 'feature'
            },
            {
                'title': 'تخصيص الإعدادات',
                'description': 'قم بتخصيص إعدادات البوت لتناسب احتياجاتك',
                'action': 'customize_settings',
                'priority': 'low',
                'category': 'settings'
            },
            {
                'title': 'استكشاف الميزات الجديدة',
                'description': 'تعرف على آخر الميزات المضافة للبوت',
                'action': 'check_new_features',
                'priority': 'low',
                'category': 'tip'
            }
        ]

