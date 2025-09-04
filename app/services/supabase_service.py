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
    
    async def find_cities_by_name(self, city_name: str) -> List[Dict[str, Any]]:
        """동일 이름 도시 검색"""
        try:
            if not self.is_connected():
                return []
            
            # 관계 조인 없이 단순 조회로 변경 (관계 설정 문제 회피)
            response = self.client.table('cities').select('*').ilike('name', f'%{city_name}%').execute()
            
            cities = []
            for city in response.data:
                # 별도로 country와 region 정보 조회
                country_name = "Unknown"
                region_name = ""
                
                try:
                    if city.get('region_id'):
                        region_resp = self.client.table('regions').select('name, country_id').eq('id', city['region_id']).execute()
                        if region_resp.data:
                            region_name = region_resp.data[0].get('name', '')
                            country_id = region_resp.data[0].get('country_id')
                            if country_id:
                                country_resp = self.client.table('countries').select('name').eq('id', country_id).execute()
                                if country_resp.data:
                                    country_name = country_resp.data[0].get('name', 'Unknown')
                except Exception as join_error:
                    logger.warning(f"관계 조회 실패: {join_error}")
                
                cities.append({
                    'city_id': city['id'],
                    'city_name': city['name'],
                    'country_name': country_name,
                    'region_name': region_name
                })
            
            return cities
            
        except Exception as e:
            logger.error(f"도시 검색 실패: {e}")
            return []

    async def get_all_cached_places_by_city(self, city_id: int) -> List[Dict[str, Any]]:
        """도시별 모든 캐시된 장소 조회"""
        try:
            if not self.is_connected():
                return []
            
            response = self.client.table('cached_places').select('*').eq('city_id', city_id).execute()
            
            places = []
            for place in response.data:
                place_data = {
                    'place_id': place.get('place_id'),
                    'name': place.get('name'),
                    'category': place.get('category'),
                    'address': place.get('address'),
                    'rating': place.get('rating'),
                    'photo_url': place.get('photo_url', ''),
                    'website': place.get('website_url', ''),  # 🔥 핵심 수정: website_url로 수정
                    'coordinates': {
                        'lat': place.get('latitude', 0.0),
                        'lng': place.get('longitude', 0.0)
                    }
                }
                # 캐시 데이터 로깅
                logger.error(f"🔍 [CACHE_DATA] Place: {place_data['name']}, website: {place_data['website']}, photo_url: {place_data['photo_url']}")
                places.append(place_data)
            
            return places
            
        except Exception as e:
            logger.error(f"캐시된 장소 조회 실패: {e}")
            return []

    async def get_ai_settings(self) -> Dict[str, Any]:
        """AI 설정 조회 (기존 settings 테이블만 사용)"""
        logger.info("🔍 [SUPABASE_GET_AI_SETTINGS] AI 설정 조회 시작")
        print("🔍 [SUPABASE_GET_AI_SETTINGS] AI 설정 조회 시작")
        
        try:
            logger.info(f"📊 [CONNECTION_CHECK] Supabase 연결 상태: {self.is_connected()}")
            print(f"📊 [CONNECTION_CHECK] Supabase 연결 상태: {self.is_connected()}")
            
            if not self.is_connected():
                logger.warning("⚠️ [NO_CONNECTION] Supabase 연결 없음, 기본 설정 반환")
                print("⚠️ [NO_CONNECTION] Supabase 연결 없음, 기본 설정 반환")
                return self._get_default_ai_settings()
            
            logger.info("🔍 [TABLE_QUERY] settings 테이블 조회 시작")
            print("🔍 [TABLE_QUERY] settings 테이블 조회 시작")
            
            # 기존 settings 테이블 사용
            try:
                logger.info("🚀 [ACTUAL_QUERY] 실제 Supabase 테이블 쿼리 실행")
                print("🚀 [ACTUAL_QUERY] 실제 Supabase 테이블 쿼리 실행")
                
                response = self.client.table('settings').select('*').execute()
                
                logger.info("✅ [QUERY_SUCCESS] Supabase 쿼리 실행 성공")
                logger.info(f"📊 [RESPONSE_DATA] 응답 데이터: {response.data}")
                logger.info(f"📊 [DATA_COUNT] 조회된 설정 수: {len(response.data) if response.data else 0}")
                print(f"✅ [QUERY_SUCCESS] Supabase 쿼리 성공, 데이터 수: {len(response.data) if response.data else 0}")
                
                if response.data:
                    logger.info("🔧 [DATA_PROCESSING] 설정 데이터 처리 시작")
                    print("🔧 [DATA_PROCESSING] 설정 데이터 처리 시작")
                    
                    settings_dict = {item['key']: item['value'] for item in response.data}
                    logger.info(f"📊 [SETTINGS_DICT] 변환된 설정 딕셔너리: {settings_dict}")
                    
                    result = {
                        'provider': settings_dict.get('default_provider', 'openai'),
                        'openai_model': settings_dict.get('openai_model_name', 'gpt-4'),
                        'gemini_model': settings_dict.get('gemini_model_name', 'gemini-1.5-flash'),
                        'temperature': 0.7,
                        'max_tokens': 2000
                    }
                    
                    logger.info(f"✅ [RESULT_SUCCESS] 최종 AI 설정: {result}")
                    print(f"✅ [RESULT_SUCCESS] 최종 AI 설정: {result}")
                    return result
                else:
                    logger.warning("⚠️ [EMPTY_DATA] settings 테이블에 데이터가 없습니다")
                    print("⚠️ [EMPTY_DATA] settings 테이블에 데이터가 없습니다")
                    
                    logger.info("🔄 [DEFAULT_FALLBACK] 기본 설정 사용")
                    print("🔄 [DEFAULT_FALLBACK] 기본 설정 사용")
                    return self._get_default_ai_settings()
                    
            except Exception as query_error:
                logger.error(f"❌ [QUERY_ERROR] Supabase 쿼리 실행 실패: {query_error}")
                logger.error(f"📊 [QUERY_ERROR_TYPE] 쿼리 에러 타입: {type(query_error).__name__}")
                logger.error(f"📊 [QUERY_ERROR_MSG] 쿼리 에러 메시지: {str(query_error)}")
                print(f"❌ [QUERY_ERROR] Supabase 쿼리 실행 실패: {query_error}")
                
                # 특정 에러 타입별 처리
                error_msg = str(query_error).lower()
                if 'relation' in error_msg and 'does not exist' in error_msg:
                    logger.error("💥 [TABLE_NOT_EXISTS] settings 테이블이 존재하지 않습니다")
                    print("💥 [TABLE_NOT_EXISTS] settings 테이블이 존재하지 않습니다")
                elif 'permission denied' in error_msg:
                    logger.error("🚫 [PERMISSION_DENIED] settings 테이블 접근 권한이 없습니다")
                    print("🚫 [PERMISSION_DENIED] settings 테이블 접근 권한이 없습니다")
                elif 'connection' in error_msg:
                    logger.error("🔌 [CONNECTION_ERROR] Supabase 연결 문제")
                    print("🔌 [CONNECTION_ERROR] Supabase 연결 문제")
                
                raise query_error
                
        except Exception as e:
            logger.error(f"❌ [GET_AI_SETTINGS_ERROR] AI 설정 조회 최종 실패: {e}")
            logger.error(f"📊 [ERROR_TYPE] 에러 타입: {type(e).__name__}")
            logger.error(f"📊 [ERROR_MSG] 에러 메시지: {str(e)}")
            logger.error(f"📊 [ERROR_TRACEBACK] 상세 트레이스백:", exc_info=True)
            print(f"❌ [GET_AI_SETTINGS_ERROR] AI 설정 조회 최종 실패: {e}")
            
            logger.info("🔄 [FINAL_FALLBACK] 최종 폴백으로 기본 설정 반환")
            print("🔄 [FINAL_FALLBACK] 최종 폴백으로 기본 설정 반환")
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
            
            # 동기 Supabase 호출을 비동기로 래핑
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.table('prompts').select('value').eq('name', prompt_name).execute()
            )
            
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
        """국가 조회 또는 생성 (영문 표준명만 입력)"""
        try:
            logger.info(f"🌍 [COUNTRY_LOOKUP] 국가 조회/생성 시작: '{country_name}'")
            
            if not self.is_connected():
                logger.error("🚫 [COUNTRY_LOOKUP] Supabase 연결 실패")
                raise ValueError("Supabase 연결 실패. 국가 정보를 처리할 수 없습니다.")
            
            country_name = (country_name or '').strip()
            logger.info(f"🌍 [COUNTRY_LOOKUP] 정규화된 국가명: '{country_name}'")

            # 동기 Supabase 호출을 비동기로 래핑
            import asyncio
            loop = asyncio.get_event_loop()
            
            # 기존 국가 조회
            response = await loop.run_in_executor(
                None,
                lambda: self.client.table('countries').select('id').eq('name', country_name).execute()
            )
            logger.info(f"🔍 [COUNTRY_LOOKUP] 조회 결과: {len(response.data) if response.data else 0}개 발견")
            
            if response.data:
                country_id = response.data[0]['id']
                logger.info(f"✅ [COUNTRY_LOOKUP] 기존 국가 조회 성공: {country_name} (ID: {country_id})")
                return country_id
            else:
                # 새로운 국가 생성
                logger.info(f"🆕 [COUNTRY_CREATE] 새로운 국가 생성 시도: {country_name}")
                insert_response = await loop.run_in_executor(
                    None,
                    lambda: self.client.table('countries').insert({'name': country_name}).execute()
                )
                
                if insert_response.data:
                    country_id = insert_response.data[0]['id']
                    logger.info(f"✅ [COUNTRY_CREATE] 새로운 국가 생성 완료: {country_name} (ID: {country_id})")
                    return country_id
                else:
                    logger.error(f"💥 [COUNTRY_CREATE] 국가 생성 실패: 응답 데이터 없음")
                    raise ValueError(f"국가 생성 실패: {country_name}")
                    
        except Exception as e:
            logger.error(f"💥 [COUNTRY_ERROR] 국가 조회/생성 실패: {e}")
            raise ValueError(f"국가 {country_name} 처리 중 오류 발생: {str(e)}")
    
    async def get_or_create_region(self, country_id: int, region_name: str) -> int:
        """광역 행정구역(주/도) 조회 또는 생성 (영문 표준명만 입력)"""
        try:
            if not self.is_connected():
                raise ValueError("Supabase 연결 실패. 지역 정보를 처리할 수 없습니다.")

            if not region_name:
                # 지역명이 없으면 국가 단위 지역을 가상으로 생성/사용
                region_name = "_DEFAULT_"

            # 동기 Supabase 호출을 비동기로 래핑
            import asyncio
            loop = asyncio.get_event_loop()
            
            resp = await loop.run_in_executor(
                None,
                lambda: (
                    self.client
                    .table('regions')
                    .select('id')
                    .eq('name', region_name)
                    .eq('country_id', country_id)
                    .execute()
                )
            )
            if resp.data:
                return resp.data[0]['id']

            ins = await loop.run_in_executor(
                None,
                lambda: self.client.table('regions').insert({'name': region_name, 'country_id': country_id}).execute()
            )
            if ins.data:
                return ins.data[0]['id']
            raise ValueError("지역 생성 실패")
        except Exception as e:
            logger.error(f"지역 조회/생성 실패: {e}")
            raise ValueError(f"지역 처리 중 오류 발생: {str(e)}")

    async def get_or_create_city(self, region_id: int, city_name: str) -> int:
        """도시 조회 또는 생성 (영문 표준명만 입력, region_id 기반)"""
        try:
            if not self.is_connected():
                raise ValueError("Supabase 연결 실패. 도시 정보를 처리할 수 없습니다.")
            
            city_name = (city_name or '').strip()
            
            # 동기 Supabase 호출을 비동기로 래핑
            import asyncio
            loop = asyncio.get_event_loop()
            
            # 기존 도시 조회 (이름과 국가 ID로 조회)
            response = await loop.run_in_executor(
                None,
                lambda: (
                    self.client
                    .table('cities')
                    .select('id')
                    .eq('name', city_name)
                    .eq('region_id', region_id)
                    .execute()
                )
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
                insert_response = await loop.run_in_executor(
                    None,
                    lambda: self.client.table('cities').insert(insert_data).execute()
                )
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
            cached_places: List[Dict[str, Any]] = []
            for place in unique_places:
                cached_place = {
                    'city_id': city_id,
                    'place_id': place.get('place_id', ''),
                    'name': place.get('name', ''),
                    'category': place.get('category', ''),
                    'address': place.get('address', ''),
                    'rating': place.get('rating', 0.0),
                    'photo_url': place.get('photo_url', ''),
                    'website_url': place.get('website', '') or place.get('websiteUri', ''),  # 🔥 핵심 수정: website_url로 수정
                    'latitude': place.get('lat', 0.0),
                    'longitude': place.get('lng', 0.0)
                }
                cached_places.append(cached_place)

            if not cached_places:
                logger.warning("저장할 장소 데이터가 없습니다.")
                return False

            # 1) 선조회: 이미 존재하는 place_id를 수집하여 '진짜 신규'만 선별
            incoming_ids = [cp['place_id'] for cp in cached_places if cp.get('place_id')]
            try:
                existing_resp = (
                    self.client
                    .table('cached_places')
                    .select('place_id')
                    .eq('city_id', city_id)
                    .in_('place_id', incoming_ids)
                    .execute()
                )
                existing_ids = set([row['place_id'] for row in (existing_resp.data or [])])
            except Exception as se:
                # 조회 실패 시에도 전체를 신규로 간주하고 삽입 로직으로 진행
                logger.warning(f"기존 place_id 선조회 실패(무시하고 진행): {se}")
                existing_ids = set()

            new_records = [cp for cp in cached_places if cp['place_id'] not in existing_ids]
            if not new_records:
                logger.info(f"도시 ID {city_id}: 신규로 저장할 장소가 없습니다. (중복 {len(cached_places)})")
                return True

            # 2) 배치 삽입 시도
            try:
                resp = (
                    self.client
                    .table('cached_places')
                    .insert(new_records)
                    .execute()
                )
                if resp.data:
                    logger.info(f"도시 ID {city_id}에 신규 {len(new_records)}개 장소 저장 완료")
                    return True
                # 데이터가 비어있어도 에러가 없다면 성공으로 간주
                logger.info("배치 삽입 응답에 데이터가 없지만 에러 없음. 계속 진행")
                return True
            except Exception as be:
                # 3) 중복/경합 등으로 인한 배치 실패 폴백: 개별 삽입으로 지속
                error_msg = str(be)
                logger.warning(f"배치 삽입 중 오류 발생, 폴백 수행: {error_msg}")
                success_count = 0
                for rec in new_records:
                    try:
                        r = self.client.table('cached_places').insert(rec).execute()
                        if r.data:
                            success_count += 1
                    except Exception as ie:
                        msg = str(ie)
                        # 여전히 duplicate 발생 시 무시하고 계속
                        if 'duplicate key' in msg or '23505' in msg:
                            logger.info(f"중복 place_id 무시: {rec.get('place_id')}")
                            continue
                        logger.error(f"단일 삽입 실패: {msg}")
                        continue
                if success_count > 0:
                    logger.info(f"개별 삽입 폴백 성공: {success_count}/{len(new_records)}")
                    return True
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

    async def get_cached_place_by_place_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """place_id로 캐시된 장소 조회 (중복 확인용)"""
        try:
            if not self.is_connected():
                return None

            response = (
                self.client
                .table('cached_places')
                .select('*')
                .eq('place_id', place_id)
                .execute()
            )
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"place_id로 캐시 조회 실패: {e}")
            return None

    async def save_cached_place(self, place_data: Dict[str, Any]) -> bool:
        """개별 장소를 캐시에 저장"""
        try:
            if not self.is_connected():
                raise ValueError("Supabase 연결 실패")

            # coordinates 처리
            coordinates = place_data.get('coordinates', {})
            
            insert_data = {
                'city_id': place_data.get('city_id'),
                'place_id': place_data.get('place_id'),
                'name': place_data.get('name'),
                'category': place_data.get('category'),
                'address': place_data.get('address', ''),
                'rating': place_data.get('rating', 0.0),
                'photo_url': place_data.get('photo_url', ''),
                'website_url': place_data.get('website', '') or place_data.get('websiteUri', ''),  # 웹사이트 URL 추가
                'latitude': coordinates.get('lat', 0.0),
                'longitude': coordinates.get('lng', 0.0)
            }
            
            response = self.client.table('cached_places').insert(insert_data).execute()
            return bool(response.data)
            
        except Exception as e:
            # 중복 키 에러는 무시
            if 'duplicate key' in str(e) or '23505' in str(e):
                logger.info(f"중복 place_id 무시: {place_data.get('place_id')}")
                return True
            logger.error(f"개별 장소 저장 실패: {e}")
            return False
    

    

    

    

    
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