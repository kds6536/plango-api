"""
새로운 장소 추천 서비스 (v6.0)
새로운 데이터베이스 스키마(countries, cities, cached_places, prompts)에 맞춰 설계된 장소 추천 시스템
"""

import json
import logging
from typing import Dict, List, Any, Optional
from string import Template
from app.services.supabase_service import supabase_service
from app.services.dynamic_ai_service import DynamicAIService
from app.services.google_places_service import GooglePlacesService
from app.schemas.place import PlaceRecommendationRequest, PlaceRecommendationResponse
from app.utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


class PlaceRecommendationService:
    """새로운 장소 추천 서비스"""
    
    def __init__(self):
        self.supabase = supabase_service
        self.ai_service = DynamicAIService()
        from app.services.google_places_service import GooglePlacesService
        self.google_places_service = GooglePlacesService()
    
    async def generate_place_recommendations(
        self, 
        request: PlaceRecommendationRequest
    ) -> PlaceRecommendationResponse:
        """
        메인 장소 추천 함수
        새로운 DB 구조를 활용한 중복 방지 및 프롬프트 동적 생성
        """
        try:
            logger.info(f"장소 추천 요청: {request.city}, {request.country}")
            
            # === 고도화된 아키텍처 적용 ===
            logger.info(f"🎯 [ADVANCED_MODE] 고도화된 장소 추천 모드 활성화")
            
            # 1. 국가와 도시 ID 확보 (Get-or-Create)
            city_id = await self.supabase.get_or_create_city(
                city_name=request.city,
                country_name=request.country
            )
            logger.info(f"🏙️ [CITY_ID] 도시 ID 확보: {city_id}")
            
            # 2. 기존 추천 장소 이름 목록 조회 (중복 방지용)
            existing_place_names = await self.supabase.get_existing_place_names(city_id)
            logger.info(f"📋 [EXISTING_PLACES] 기존 장소 {len(existing_place_names)}개 발견")
            
            # 3. AI 검색 계획 수립 (핵심 새 기능)
            logger.info(f"🧠 [AI_SEARCH_STRATEGY] AI 검색 계획 수립 시작")
            search_queries = await self.ai_service.create_search_queries(
                city=request.city,
                country=request.country,
                existing_places=existing_place_names
            )
            logger.info(f"📋 [SEARCH_STRATEGY] AI 검색 계획 완료: {search_queries}")
            
            # 4. 병렬 Google Places API 호출 + 재시도 로직
            logger.info(f"🚀 [PARALLEL_API_CALLS] 병렬 Google Places API 호출 시작")
            categorized_places = await self.google_places_service.parallel_search_by_categories(
                search_queries=search_queries,
                target_count_per_category=10
            )
            logger.info(f"✅ [API_CALLS_COMPLETE] 병렬 API 호출 완료")
            
            # 5. 결과 데이터 후처리 및 한글 키 매핑  
            recommendations = self._convert_to_korean_categories(categorized_places)
            
            # 6. 새로운 장소들을 cached_places에 저장
            if recommendations:
                await self._save_new_places(city_id, recommendations)
                logger.info(f"💾 [CACHE_SAVE] 새로운 장소들 캐시 저장 완료")
            
            # 7. 응답 생성
            total_new_places = sum(len(places) for places in recommendations.values())
            return PlaceRecommendationResponse(
                success=True,
                city_id=city_id,
                main_theme="AI 고도화 검색",
                recommendations=recommendations,
                previously_recommended_count=len(existing_place_names),
                newly_recommended_count=total_new_places
            )
            
        except Exception as e:
            logger.error(f"❌ [ADVANCED_ERROR] 고도화 추천 실패: {e}")
            # 폴백: 기존 방식으로 재시도
            logger.info(f"🔄 [FALLBACK] 기존 방식으로 폴백 시도")
            return await self._fallback_to_legacy_recommendation(request)
    
    def _convert_to_korean_categories(self, categorized_places: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[str]]:
        """영문 카테고리를 한글 카테고리로 변환하고 장소명만 추출"""
        category_mapping = {
            "tourism": "볼거리",
            "food": "먹거리", 
            "activity": "즐길거리",
            "accommodation": "숙소"
        }
        
        korean_recommendations = {}
        for eng_category, places in categorized_places.items():
            korean_category = category_mapping.get(eng_category, eng_category)
            place_names = [place.get("name", "Unknown Place") for place in places]
            korean_recommendations[korean_category] = place_names
            
        return korean_recommendations
    
    async def _fallback_to_legacy_recommendation(self, request: PlaceRecommendationRequest) -> PlaceRecommendationResponse:
        """기존 방식으로 폴백 (AI 프롬프트 기반)"""
        try:
            logger.info(f"🔄 [LEGACY_MODE] 기존 방식으로 폴백 실행")
            
            city_id = await self.supabase.get_or_create_city(
                city_name=request.city,
                country_name=request.country
            )
            
            existing_place_names = await self.supabase.get_existing_place_names(city_id)
            
            # 기존 방식: 프롬프트 기반 AI 추천
            dynamic_prompt = await self._create_dynamic_prompt(request, existing_place_names)
            ai_recommendations = await self._get_ai_recommendations(dynamic_prompt)
            
            if not ai_recommendations:
                raise ValueError("AI 추천 결과가 없습니다.")
            
            # Google Places API로 장소 정보 강화
            enriched_places = await self._enrich_place_data(ai_recommendations, request.city)
            
            if enriched_places:
                await self._save_new_places(city_id, enriched_places)
            
            return PlaceRecommendationResponse(
                success=True,
                city_id=city_id,
                main_theme="기존 방식 폴백",
                recommendations=enriched_places,
                previously_recommended_count=len(existing_place_names),
                newly_recommended_count=sum(len(places) for places in enriched_places.values())
            )
            
        except Exception as e:
            logger.error(f"❌ [LEGACY_FALLBACK_ERROR] 폴백 실행도 실패: {e}")
            raise ValueError(f"모든 추천 방식 실패: {str(e)}")

    async def _create_dynamic_prompt(
        self, 
        request: PlaceRecommendationRequest, 
        existing_places: List[str]
    ) -> str:
        """프롬프트 동적 생성"""
        try:
            # prompts 테이블에서 place_recommendation_v2 우선 조회, 실패 시 v1 사용
            try:
                base_prompt = await self.supabase.get_master_prompt("place_recommendation_v2")
            except Exception:
                try:
                    base_prompt = await self.supabase.get_master_prompt("place_recommendation_v1")
                except Exception as e:
                    error_msg = f"Supabase 프롬프트 로드 실패: {e}"
                    logger.warning(f"⚠️ [FALLBACK] {error_msg}")
                    
                    # 관리자에게 폴백 모드 알림
                    self._notify_admin_fallback_mode(error_msg)
                    
                    base_prompt = self._get_fallback_place_recommendation_prompt()
            
            # 기존 추천 장소 목록을 문자열로 변환
            if existing_places:
                previously_recommended_text = f"""
이미 추천된 장소들 (중복 금지):
{', '.join(existing_places)}

위 장소들과 중복되지 않는 새로운 장소만 추천해주세요."""
            else:
                previously_recommended_text = "첫 번째 추천이므로 제약 없이 최고의 장소들을 추천해주세요."
            
            # Template.safe_substitute를 사용하여 안전하게 변수 치환
            # 이 방법은 중괄호가 있는 JSON 예시에서도 안전함
            template = Template(base_prompt)
            dynamic_prompt = template.safe_substitute(
                city=request.city,
                country=request.country,
                duration_days=request.total_duration,  # total_duration → duration_days 매핑
                previously_recommended_places=previously_recommended_text
            )
            
            logger.info(f"동적 프롬프트 생성 완료 (기존 장소 {len(existing_places)}개 제외)")
            return dynamic_prompt
            
        except Exception as e:
            logger.error(f"프롬프트 생성 실패: {e}")
            raise ValueError(f"프롬프트 생성 중 오류 발생: {str(e)}")
    
    async def _get_ai_recommendations(self, prompt: str) -> Dict[str, Any]:
        """AI에게 장소 추천 요청"""
        try:
            logger.info("AI 장소 추천 요청 시작")
            
            # DynamicAIService를 통해 AI 요청
            ai_response = await self.ai_service.generate_text(
                prompt=prompt,
                max_tokens=2000
            )
            
            # AI 응답 로깅 (디버깅용)
            logger.info(f"AI 원본 응답: {ai_response[:500]}...")
            
            # JSON 파싱 강화
            try:
                # 응답에서 JSON 부분만 추출 (마크다운 코드 블록 제거)
                cleaned_response = self._extract_json_from_response(ai_response)
                recommendations = json.loads(cleaned_response)
                logger.info(f"AI 추천 결과 파싱 성공: {len(recommendations)}개 카테고리")
                return recommendations
            except json.JSONDecodeError as e:
                logger.error(f"AI 응답 JSON 파싱 실패: {e}")
                logger.error(f"파싱 시도한 응답: {cleaned_response[:200]}...")
                raise ValueError(f"AI 응답 형식 오류: {str(e)}")
                
        except Exception as e:
            logger.error(f"AI 추천 요청 실패: {e}")
            raise ValueError(f"AI 추천 중 오류 발생: {str(e)}")
    
    def _extract_json_from_response(self, response: str) -> str:
        """AI 응답에서 JSON 부분만 추출"""
        try:
            # 마크다운 코드 블록 제거
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end != -1:
                    return response[start:end].strip()
            
            # 일반 JSON 객체 찾기
            if "{" in response and "}" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                return response[start:end].strip()
            
            # 기본값: 전체 응답 반환
            return response.strip()
            
        except Exception as e:
            logger.warning(f"JSON 추출 실패: {e}")
            return response.strip()
    
    async def _enrich_place_data(
        self, 
        ai_recommendations: Dict[str, Any], 
        city: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Google Places API로 장소 정보 강화"""
        try:
            logger.info("Google Places API 장소 정보 강화 시작")
            
            enriched_results = {}
            category_mapping = {
                "tourism": "tourist_attraction",
                "food": "restaurant", 
                "activity": "amusement_park",
                "accommodation": "lodging"
            }
            
            # 카테고리명 한글 변환
            category_translation = {
                "tourism": "볼거리",
                "food": "먹거리",
                "activity": "즐길거리", 
                "accommodation": "숙소"
            }
            
            for category, place_names in ai_recommendations.items():
                if not isinstance(place_names, list):
                    continue
                
                translated_category = category_translation.get(category, category)
                logger.info(f"{translated_category} 카테고리 처리: {len(place_names)}개 장소")
                
                enriched_places = []
                for place_name in place_names:
                    try:
                        # Google Places API 검색
                        places = await self.google_places_service.search_places(
                            query=f"{place_name} {city}",
                            location=city,
                            place_type=category_mapping.get(category)
                        )
                        
                        if places:
                            # 첫 번째 결과를 선택하고 카테고리 정보 추가
                            place = places[0]
                            place['category'] = translated_category
                            enriched_places.append(place)
                            logger.debug(f"{place_name} 정보 강화 완료")
                        else:
                            logger.warning(f"{place_name} 검색 결과 없음")
                            
                    except Exception as e:
                        logger.warning(f"{place_name} 정보 강화 실패: {e}")
                        continue
                
                enriched_results[translated_category] = enriched_places
                logger.info(f"{translated_category} 카테고리 완료: {len(enriched_places)}개 장소")
            
            return enriched_results
            
        except Exception as e:
            logger.error(f"장소 정보 강화 실패: {e}")
            raise ValueError(f"장소 정보 강화 중 오류 발생: {str(e)}")
    
    async def _save_new_places(
        self, 
        city_id: int, 
        enriched_places: Dict[str, List[Dict[str, Any]]]
    ) -> bool:
        """새로운 장소들을 cached_places에 저장"""
        try:
            logger.info("새로운 장소 cached_places에 저장 시작")
            
            # 모든 카테고리의 장소를 하나의 리스트로 합치기
            all_places = []
            for category, places in enriched_places.items():
                all_places.extend(places)
            
            if all_places:
                success = await self.supabase.save_cached_places(city_id, all_places)
                if success:
                    logger.info(f"총 {len(all_places)}개 장소 저장 완료")
                else:
                    logger.warning("장소 저장 실패")
                return success
            else:
                logger.warning("저장할 장소가 없음")
                return False
                
        except Exception as e:
            logger.error(f"장소 저장 실패: {e}")
            return False

    def _get_fallback_place_recommendation_prompt(self) -> str:
        """Supabase 프롬프트 로드 실패 시 사용할 내장 폴백 프롬프트"""
        return """당신은 세계 최고의 여행 전문가 '플랜고 AI'입니다. 사용자의 여행 정보를 바탕으로 맞춤형 장소를 추천해주세요.

**사용자 여행 정보:**
- 도시: $city
- 국가: $country
- 여행 기간: $total_duration일
- 여행자 수: $travelers_count명
- 예산: $budget_range
- 여행 스타일: $travel_style

$previously_recommended_places

**추천 요구사항:**
1. 각 카테고리별로 다양하고 특색 있는 장소 추천
2. 현지인들이 실제로 가는 숨겨진 맛집과 명소 포함
3. 사용자의 예산과 여행 스타일에 맞는 장소 선별
4. 관광지는 유명한 곳과 로컬한 곳을 적절히 조합

**카테고리별 추천 개수 (최소 5개씩):**
- 볼거리(관광지): 8-12개
- 먹거리(음식점): 8-12개  
- 즐길거리(액티비티): 6-10개
- 숙소: 4-8개

**도시별 추천 예시:**
- 도쿄: 시부야, 하라주쿠, 아사쿠사, 긴자, 롯폰기
- 서울: 홍대, 강남, 명동, 이태원, 북촌한옥마을
- 부산: 해운대, 광안리, 태종대, 감천문화마을, 용두산공원

**JSON 출력 형식 (반드시 이 형식으로만):**
{{
  "볼거리": ["장소명1", "장소명2", "장소명3", "장소명4", "장소명5"],
  "먹거리": ["맛집명1", "맛집명2", "맛집명3", "맛집명4", "맛집명5"],
  "즐길거리": ["액티비티명1", "액티비티명2", "액티비티명3", "액티비티명4"],
  "숙소": ["숙소명1", "숙소명2", "숙소명3", "숙소명4"]
}}

⚠️ 중요: 반드시 JSON 형식으로만 답변해주세요. 다른 설명이나 마크다운 문법은 포함하지 마세요."""

    def _notify_admin_fallback_mode(self, error_details: str):
        """관리자에게 폴백 모드 사용을 알림"""
        import logging
        admin_logger = logging.getLogger("admin_notifications")
        
        notification_message = f"""
🚨 [ADMIN ALERT] Plango 시스템이 폴백 모드로 전환되었습니다!

📅 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🌐 환경: Railway Production
🔧 문제 유형: Supabase prompts 테이블 접근 실패
❌ 오류 상세: {error_details}

📊 현재 상태:
- Supabase 연결: {'정상' if self.supabase.is_connected() else '실패'}
- AI 서비스: {'정상' if self.ai_service else '실패'}
- 폴백 시스템: 활성화됨

💡 권장 조치사항:
1. Supabase prompts 테이블 존재 여부 확인
2. Railway 환경변수 SUPABASE_URL, SUPABASE_KEY 확인
3. Supabase 프로젝트 권한 설정 확인
4. 필요시 prompts 테이블 재생성

🔗 확인 링크:
- Railway 대시보드: https://railway.com/dashboard
- Supabase 대시보드: https://supabase.com/dashboard

⚠️ 이 알림은 시스템 안정성을 위해 자동으로 생성되었습니다.
        """
        
        # 로그에 기록
        admin_logger.warning(notification_message)
        
        # 콘솔에 출력 (개발/디버깅용)
        print("=" * 80)
        print("🚨 ADMIN ALERT: FALLBACK MODE ACTIVATED")
        print("=" * 80)
        print(notification_message)
        print("=" * 80)
        
        # 추후 Slack, Discord, Email 등으로 확장 가능
        # await self._send_admin_notification(notification_message)


# 전역 인스턴스
place_recommendation_service = PlaceRecommendationService()