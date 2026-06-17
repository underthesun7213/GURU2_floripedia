import json
import os

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def update_plant_images(categorized_file, details_file, output_file):
    # 1. 파일 로드
    with open(categorized_file, 'r', encoding='utf-8') as f:
        categorized_plants = json.load(f)

    with open(details_file, 'r', encoding='utf-8') as f:
        flowers_detail = json.load(f)

    # 2. 꽃 상세 정보에서 이름(flowNm)을 키로 하여 이미지 URL 매핑 생성
    detail_map = {}
    for item in flowers_detail:
        name = item.get('flowNm')
        if not name:
            continue
        
        images = []
        # imgUrl1, imgUrl2, imgUrl3 확인하여 리스트에 추가
        for i in range(1, 4):
            url = item.get(f'imgUrl{i}')
            if url and url.strip():
                images.append(url)
        
        detail_map[name] = images

    # 3. categorized_plants에 images 필드 추가 및 업데이트
    updated_count = 0
    for plant in categorized_plants:
        name = plant.get('name')
        
        if name in detail_map:
            plant['images'] = detail_map[name]
            updated_count += 1
        else:
            # 매칭되는 정보가 없으면 기존 imageUrl을 리스트로 유지
            current_url = plant.get('imageUrl')
            plant['images'] = [current_url] if current_url else []

    # 4. 결과 저장 (added_images.json)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(categorized_plants, f, indent=4, ensure_ascii=False)

    print(f"작업 완료: {output_file} 파일이 생성되었습니다. (업데이트된 식물 수: {updated_count})")

if __name__ == "__main__":
    data_dir = os.path.join(BACKEND_DIR, 'data')
    update_plant_images(
        os.path.join(data_dir, 'categorized_plants.json'),
        os.path.join(data_dir, 'flowers_detail.json'),
        os.path.join(data_dir, 'added_images.json'),
    )