import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)


class GeminiService:
    """Gemini API 서비스 클래스"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-pro')
    
    async def generate_text(self, prompt: str) -> str:
        """텍스트 생성"""
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API 오류: {str(e)}")
    
    async def analyze_image(self, image_data: bytes, prompt: str) -> str:
        """이미지 분석"""
        try:
            model = genai.GenerativeModel('gemini-pro-vision')
            response = await model.generate_content_async([prompt, image_data])
            return response.text
        except Exception as e:
            raise Exception(f"Gemini Vision API 오류: {str(e)}")
