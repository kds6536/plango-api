"""
Supabase 연동 서비스
AI 설정 및 프롬프트 관리를 위한 Supabase 연결
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from supabase import create_client, Client
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SupabaseService:
    """Supabase 연동 서비스"""
    
    def __init__(self):
        """Supabase 클라이언트 초기화"""
        try:
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                logger.warning("Supabase 설정이 없습니다. 로컬 파일을 사용합니다.")
                self.client = None
                return
                
            self.client: Client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_KEY
            )
            logger.info("Supabase 클라이언트 초기화 완료")
            
        except Exception as e:
            logger.error(f"Supabase 클라이언트 초기화 실패: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """Supabase 연결 상태 확인"""
        return self.client is not None
    
    async def get_ai_settings(self) -> Dict[str, Any]:
        """AI 설정 조회 (기존 settings 테이블만 사용)"""
        try:
            if not self.is_connected():
                return self._get_default_ai_settings()
            
            # 기존 settings 테이블 사용
            response = self.client.table('settings').select('*').execute()
            if response.data:
                settings_dict = {item['key']: item['value'] for item in response.data}
                return {
                    'provider': settings_dict.get('default_provider', 'openai'),
                    'openai_model': settings_dict.get('openai_model_name', 'gpt-4'),
                    'gemini_model': settings_dict.get('gemini_model_name', 'gemini-1.5-flash'),
                    'temperature': 0.7,
                    'max_tokens': 2000
                }
            else:
                logger.warning("AI 설정이 없습니다. 기본값을 사용합니다.")
                return self._get_default_ai_settings()
                
        except Exception as e:
            logger.error(f"AI 설정 조회 실패: {e}")
            return self._get_default_ai_settings()
    
    async def update_ai_settings(self, settings_data: Dict[str, Any]) -> bool:
        """AI 설정 업데이트"""
        try:
            if not self.is_connected():
                raise ValueError("Supabase 연결 실패. AI 설정을 업데이트할 수 없습니다.")
            
            # 기존 settings 테이블 업데이트
            provider = settings_data.get('provider', 'openai')
            openai_model = settings_data.get('openai_model', 'gpt-4')
            gemini_model = settings_data.get('gemini_model', 'gemini-1.5-flash')
            
            updates = [
                {'key': 'default_provider', 'value': provider, 'is_encrypted': False},
                {'key': 'openai_model_name', 'value': openai_model, 'is_encrypted': False},
                {'key': 'gemini_model_name', 'value': gemini_model, 'is_encrypted': False}
            ]
            
            for update in updates:
                self.client.table('settings').upsert(update).execute()
            
            logger.info(f"AI 설정 업데이트 완료: {settings_data}")
            return True
            
        except Exception as e:
            logger.error(f"AI 설정 업데이트 실패: {e}")
            return False
    
    async def get_master_prompt(self, prompt_name: str) -> str:
        """마스터 프롬프트 조회 (name 컬럼으로 조회, prompts 테이블 부재 시 예외 발생)"""
        try:
            if not self.is_connected():
                logger.warning(f"⚠️ Supabase 연결 없음 - {prompt_name} 프롬프트 조회 실패")
                raise ValueError(f"Supabase 연결 실패. {prompt_name} 프롬프트를 조회할 수 없습니다.")
            
            # name 컬럼으로 조회
            response = self.client.table('prompts').select('value').eq('name', prompt_name).execute()
            
            if response.data:
                logger.info(f"✅ Supabase에서 프롬프트 조회 성공: {prompt_name}")
                return response.data[0]['value']
            else:
                logger.warning(f"⚠️ {prompt_name} 프롬프트가 prompts 테이블에 존재하지 않음")
                raise ValueError(f"{prompt_name} 프롬프트가 prompts 테이블에 존재하지 않습니다.")
                
        except Exception as e:
            # prompts 테이블이 존재하지 않는 경우 특별 처리
            error_msg = str(e)
            if "relation \"public.prompts\" does not exist" in error_msg:
                logger.warning(f"⚠️ prompts 테이블이 존재하지 않음 - {prompt_name} 프롬프트 조회 불가")
                raise ValueError(f"prompts 테이블이 존재하지 않습니다. {prompt_name} 프롬프트를 조회할 수 없습니다.")
            else:
                logger.error(f"❌ 마스터 프롬프트 조회 실패: {e}")
                raise ValueError(f"{prompt_name} 프롬프트 조회 중 오류 발생: {error_msg}")
    
    # =============================================================================
    # 새로운 DB 스키마 관련 함수들 (countries, cities, cached_places)
    # =============================================================================
    
    async def get_or_create_country(self, country_name: str) -> int:
        """국가 조회 또는 생성 (Get-or-Create 로직)"""
        try:
            if not self.is_connected():
                raise ValueError("Supabase 연결 실패. 국가 정보를 처리할 수 없습니다.")
            
            # 다국어 표기 정규화
            def normalize_country_name(name: str) -> str:
                if not name:
                    return name
                name = name.strip()
                mapping = {
                    # East Asia
                    "대한민국": "South Korea",
                    "한국": "South Korea",
                    "South Korea": "South Korea",
                    "Republic of Korea": "South Korea",
                    "韓国": "South Korea",
                    "Korea": "South Korea",
                    "日本": "Japan",
                    "일본": "Japan",
                    "Japan": "Japan",
                    # Common
                    "United States": "United States",
                    "USA": "United States",
                    "미국": "United States",
                    "中國": "China",
                    "中国": "China",
                    "중국": "China",
                    "France": "France",
                    "프랑스": "France",
                    "Italia": "Italy",
                    "이탈리아": "Italy",
                    "スペイン": "Spain",
                    "스페인": "Spain",
                    "독일": "Germany",
                    "ドイツ": "Germany",
                    "Germany": "Germany",
                    "영국": "United Kingdom",
                    "United Kingdom": "United Kingdom",
                    "UK": "United Kingdom",
                    "Thailand": "Thailand",
                    "태국": "Thailand",
                    "Vietnam": "Vietnam",
                    "베트남": "Vietnam",
                    "Singapore": "Singapore",
                    "싱가포르": "Singapore",
                }
                return mapping.get(name, name)

            country_name = normalize_country_name(country_name)

            # 기존 국가 조회
            response = self.client.table('countries').select('id').eq('name', country_name).execute()
            
            if response.data:
                country_id = response.data[0]['id']
                logger.info(f"기존 국가 조회 성공: {country_name} (ID: {country_id})")
                return country_id
            else:
                # 새로운 국가 생성
                insert_response = self.client.table('countries').insert({'name': country_name}).execute()
                if insert_response.data:
                    country_id = insert_response.data[0]['id']
                    logger.info(f"새로운 국가 생성 완료: {country_name} (ID: {country_id})")
                    return country_id
                else:
                    raise ValueError(f"국가 생성 실패: {country_name}")
                    
        except Exception as e:
            logger.error(f"국가 조회/생성 실패: {e}")
            raise ValueError(f"국가 {country_name} 처리 중 오류 발생: {str(e)}")
    
    async def get_or_create_region(self, country_id: int, region_name: str) -> int:
        """광역 행정구역(주/도) 조회 또는 생성"""
        try:
            if not self.is_connected():
                raise ValueError("Supabase 연결 실패. 지역 정보를 처리할 수 없습니다.")

            if not region_name:
                # 지역명이 없으면 국가 단위 지역을 가상으로 생성/사용
                region_name = "_DEFAULT_"

            resp = (
                self.client
                .table('regions')
                .select('id')
                .eq('name', region_name)
                .eq('country_id', country_id)
                .execute()
            )
            if resp.data:
                return resp.data[0]['id']

            ins = self.client.table('regions').insert({'name': region_name, 'country_id': country_id}).execute()
            if ins.data:
                return ins.data[0]['id']
            raise ValueError("지역 생성 실패")
        except Exception as e:
            logger.error(f"지역 조회/생성 실패: {e}")
            raise ValueError(f"지역 처리 중 오류 발생: {str(e)}")

    async def get_or_create_city(self, region_id: int, city_name: str) -> int:
        """도시 조회 또는 생성 (Get-or-Create 로직, region_id 기반)"""
        try:
            if not self.is_connected():
                raise ValueError("Supabase 연결 실패. 도시 정보를 처리할 수 없습니다.")
            
            # 도시명 정규화(간단 매핑)
            def normalize_city_name(name: str) -> str:
                if not name:
                    return name
                name = name.strip()
                mapping = {
                    # Japan
                    "도쿄": "Tokyo",
                    "東京": "Tokyo",
                    "오사카": "Osaka",
                    "大阪": "Osaka",
                    "교토": "Kyoto",
                    "京都": "Kyoto",
                    # Korea
                    "서울": "Seoul",
                    "부산": "Busan",
                    "제주": "Jeju",
                    # China
                    "베이징": "Beijing",
                    "北京": "Beijing",
                    "상하이": "Shanghai",
                    "上海": "Shanghai",
                    # US/EU common
                    "뉴욕": "New York",
                    "로스앤젤레스": "Los Angeles",
                    "파리": "Paris",
                    "로마": "Rome",
                    "바르셀로나": "Barcelona",
                    "베를린": "Berlin",
                    "런던": "London",
                    "방콕": "Bangkok",
                    "호치민": "Ho Chi Minh City",
                    "싱가포르": "Singapore",
                }
                return mapping.get(name, name)

            city_name = normalize_city_name(city_name)
            
            # 기존 도시 조회 (이름과 국가 ID로 조회)
            response = (
                self.client
                .table('cities')
                .select('id')
                .eq('name', city_name)
                .eq('region_id', region_id)
                .execute()
            )
            
            if response.data:
                city_id = response.data[0]['id']
                logger.info(f"기존 도시 조회 성공: {city_name}, region_id={region_id} (ID: {city_id})")
                return city_id
            else:
                # 새로운 도시 생성
                insert_data = {
                    'name': city_name,
                    'region_id': region_id
                }
                insert_response = self.client.table('cities').insert(insert_data).execute()
                if insert_response.data:
                    city_id = insert_response.data[0]['id']
                    logger.info(f"새로운 도시 생성 완료: {city_name}, region_id={region_id} (ID: {city_id})")
                    return city_id
                else:
                    raise ValueError(f"도시 생성 실패: {city_name}, region_id={region_id}")
                    
        except Exception as e:
            logger.error(f"도시 조회/생성 실패: {e}")
            raise ValueError(f"도시 {city_name}, region_id={region_id} 처리 중 오류 발생: {str(e)}")
    
    async def get_existing_place_names(self, city_id: int) -> List[str]:
        """특정 도시의 기존 추천 장소 이름 목록 조회"""
        try:
            if not self.is_connected():
                raise ValueError("Supabase 연결 실패. 장소 정보를 조회할 수 없습니다.")
            
            # city_id로 cached_places에서 name 컬럼만 조회
            response = self.client.table('cached_places').select('name').eq('city_id', city_id).execute()
            
            if response.data:
                place_names = [place['name'] for place in response.data]
                logger.info(f"도시 ID {city_id}의 기존 장소 {len(place_names)}개 조회 완료")
                return place_names
            else:
                logger.info(f"도시 ID {city_id}에 기존 장소가 없습니다.")
                return []
                
        except Exception as e:
            logger.error(f"기존 장소 목록 조회 실패: {e}")
            raise ValueError(f"도시 ID {city_id}의 장소 목록 조회 중 오류 발생: {str(e)}")
    
    async def save_cached_places(self, city_id: int, places_data: List[Dict[str, Any]]) -> bool:
        """AI 추천 결과를 cached_places 테이블에 저장"""
        try:
            if not self.is_connected():
                raise ValueError("Supabase 연결 실패. 장소 정보를 저장할 수 없습니다.")
            
            # (city_id, place_id) 중복 제거: 여러 카테고리에서 동일 장소가 올 수 있음
            dedup_map: Dict[str, Dict[str, Any]] = {}
            for p in places_data:
                pid = str(p.get('place_id') or '').strip()
                if not pid:
                    continue
                dedup_map[pid] = p  # 같은 place_id가 오면 마지막 것이 유지

            unique_places = list(dedup_map.values())

            # 각 장소 정보를 cached_places 형식으로 변환
            cached_places = []
            for place in unique_places:
                # 현재 DB 스키마 최소 컬럼에 맞춰 저장 (city_id, place_id, name, category, address)
                cached_place = {
                    'city_id': city_id,
                    'place_id': place.get('place_id', ''),
                    'name': place.get('name', ''),
                    'category': place.get('category', ''),
                    'address': place.get('address', ''),
                }
                cached_places.append(cached_place)
            
            # 배치로 저장
            if cached_places:
                # upsert로 중복(place_id, city_id) 시 갱신되도록 처리
                insert_response = (
                    self.client
                    .table('cached_places')
                    .upsert(cached_places, on_conflict='city_id,place_id')
                    .execute()
                )
                if insert_response.data:
                    logger.info(f"도시 ID {city_id}에 {len(cached_places)}개 장소 저장 완료")
                    return True
                else:
                    raise ValueError("장소 데이터 저장 실패")
            else:
                logger.warning("저장할 장소 데이터가 없습니다.")
                return False
                
        except Exception as e:
            logger.error(f"장소 캐싱 실패: {e}")
            raise ValueError(f"장소 캐싱 중 오류 발생: {str(e)}")

    async def get_cached_places_by_category(self, city_id: int, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """카테고리별 캐시된 장소를 조회 (부족분 보충용)"""
        try:
            if not self.is_connected():
                raise ValueError("Supabase 연결 실패. 장소 정보를 조회할 수 없습니다.")

            response = (
                self.client
                .table('cached_places')
                .select('place_id, name, category, address')
                .eq('city_id', city_id)
                .eq('category', category)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"캐시 조회 실패: {e}")
            return []
    

    

    

    

    
    def _get_default_ai_settings(self) -> Dict[str, Any]:
        """기본 AI 설정 반환"""
        return {
            'provider': 'openai',
            'openai_model': 'gpt-4',
            'gemini_model': 'gemini-1.5-flash',
            'temperature': 0.7,
            'max_tokens': 2000
        }


# 전역 Supabase 서비스 인스턴스
supabase_service = SupabaseService()