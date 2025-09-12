#!/usr/bin/env python3
"""
김포를 동명 지역 목록에서 제거하는 스크립트
"""

def fix_place_recommendations():
    """place_recommendations.py에서 김포 제거"""
    
    # 파일 읽기
    with open('app/routers/place_recommendations.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 김포 관련 부분 제거
    old_gimpo_section = '''                ],
                "김포": [
                    {
                        "place_id": "ChIJzWVBSgSifDUR64Pq5LTtioU",
                        "display_name": "김포시",
                        "formatted_address": "대한민국 경기도 김포시",
                        "lat": 37.6156,
                        "lng": 126.7159
                    },
                    {
                        "place_id": "ChIJBzKw3HGifDURm_JbQKHsEX4",
                        "display_name": "김포공항",
                        "formatted_address": "대한민국 서울특별시 강서구 김포공항",
                        "lat": 37.5583,
                        "lng": 126.7906
                    }
                ]'''
    
    new_section = '''                ]'''
    
    # 모든 김포 섹션 제거
    content = content.replace(old_gimpo_section, new_section)
    
    # 파일 쓰기
    with open('app/routers/place_recommendations.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 김포 동명 지역 목록에서 제거 완료")

if __name__ == "__main__":
    fix_place_recommendations()