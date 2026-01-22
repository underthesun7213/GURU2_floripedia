import uuid
import mimetypes
from firebase_admin import storage
from app.core.config import settings

class FirebaseStorageService:
    """Firebase Storage 서비스 클래스"""

    def __init__(self):
        # [중요] 초기화는 main.py나 deps.py에서 한 번만 수행하므로 여기선 생략하거나
        # 버킷 객체만 미리 가져옵니다.
        pass

    def _get_bucket(self):
        """버킷 객체 가져오기 (Lazy Loading)"""
        # bucket 이름을 명시해야 정확하게 찾아갑니다.
        return storage.bucket(name=settings.FIREBASE_STORAGE_BUCKET)

    def upload_profile_image(self, user_id: str, file_data: bytes, content_type: str = "image/jpeg") -> str:
        """
        프로필 이미지 업로드
        """
        # 1. 파일 확장자 결정 (mime type 기반)
        extension = mimetypes.guess_extension(content_type) or ".jpg"
        
        # 2. 고유 파일명 생성
        unique_id = uuid.uuid4().hex[:8]
        file_name = f"profile_images/{user_id}/{unique_id}{extension}"

        # 3. 업로드
        bucket = self._get_bucket()
        blob = bucket.blob(file_name)
        
        # content_type을 지정해야 브라우저에서 바로 이미지로 보입니다.
        blob.upload_from_string(file_data, content_type=content_type)
        
        # 4. 공개 URL 생성
        # 주의: Firebase Console > Storage > Rules에서 read 권한이 public이어야 함
        # 또는 make_public()을 호출하여 ACL을 변경
        blob.make_public()

        return blob.public_url

    def delete_file(self, file_url: str) -> bool:
        """
        파일 삭제
        """
        if not file_url:
            return False
            
        try:
            # URL에서 파일 경로 추출 로직 개선
            # 예: https://storage.googleapis.com/download/storage/v1/b/BUCKET/o/profile_images%2Fuser%2Ffile.jpg
            # 단순히 'profile_images/'가 포함되어 있는지로 판단
            if "profile_images" not in file_url:
                return False

            # URL 디코딩 및 파싱이 복잡할 수 있으므로, 
            # 가장 확실한 방법은 DB에 저장할 때 '경로(path)'도 같이 저장하는 것이지만,
            # 여기서는 URL 파싱으로 처리합니다.
            
            # blob.public_url은 보통 이런 식입니다:
            # https://storage.googleapis.com/YOUR_BUCKET/profile_images/user/abc.jpg
            
            # 버킷 이름 뒤의 경로만 가져오기
            bucket_name = settings.FIREBASE_STORAGE_BUCKET
            if bucket_name not in file_url:
                # 다른 버킷의 파일일 수 있음
                return False
                
            # URL에서 파일명 파싱 (간단한 파싱)
            # 실제로는 urllib.parse.unquote 등을 쓰는 게 더 안전합니다.
            file_path = file_url.split(f"{bucket_name}/")[-1]
            
            bucket = self._get_bucket()
            blob = bucket.blob(file_path)
            
            if blob.exists():
                blob.delete()
                return True
            return False
            
        except Exception as e:
            print(f"파일 삭제 오류: {e}")
            return False

# 싱글톤 인스턴스
firebase_storage = FirebaseStorageService()