"""
새로운 장소 추천 서비스 (v6.0)
새로운 데이터베이스 스키마(countries, cities, cached_places, prompts)에 맞춰 설계된 장소 추천 시스템
"""

import json
import logging
from typing import Dict, List, Any, Optional
from app.services.supabase_service import supabase_service
from app.services.dynamic_ai_service import DynamicAIService
from app.services.google_places_service import GooglePlacesService
from app.schemas.place import PlaceRecommendationRequest, PlaceRecommendationResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PlaceRecommendationService:
    """새로운 장소 추천 서비스"""
    
    def __init__(self):
        self.supabase = supabase_service
        self.ai_service = DynamicAIService()
        self.google_places = GooglePlacesService()
    
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
            
            # 1. 국가와 도시 ID 확보 (Get-or-Create)
            city_id = await self.supabase.get_or_create_city(
                city_name=request.city,
                country_name=request.country
            )
            logger.info(f"도시 ID 확보: {city_id}")
            
            # 2. 기존 추천 장소 이름 목록 조회
            existing_place_names = await self.supabase.get_existing_place_names(city_id)
            logger.info(f"기존 추천 장소 {len(existing_place_names)}개 발견")
            
            # 3. 프롬프트 동적 생성
            dynamic_prompt = await self._create_dynamic_prompt(request, existing_place_names)
            
            # 4. AI에게 새로운 장소 추천 요청
            ai_recommendations = await self._get_ai_recommendations(dynamic_prompt)
            
            if not ai_recommendations:
                raise ValueError("AI 추천 결과가 없습니다.")
            
            # 5. Google Places API로 장소 정보 강화
            enriched_places = await self._enrich_place_data(ai_recommendations, request.city)
            
            # 6. 새로운 장소들을 cached_places에 저장
            if enriched_places:
                await self._save_new_places(city_id, enriched_places)
            
            # 7. 응답 생성
            return PlaceRecommendationResponse(
                success=True,
                city_id=city_id,
                main_theme="",  # 새로운 프롬프트에는 main_theme가 없음
                recommendations=enriched_places,
                previously_recommended_count=len(existing_place_names),
                newly_recommended_count=sum(len(places) for places in enriched_places.values())
            )
            
        except Exception as e:
            logger.error(f"장소 추천 실패: {e}")
            raise ValueError(f"장소 추천 중 오류 발생: {str(e)}")
    
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
                base_prompt = await self.supabase.get_master_prompt("place_recommendation_v1")
            
            # 프롬프트 템플릿 내 JSON 예시 구간의 중괄호 이스케이프 처리
            # 구분자 이후에 등장하는 {, } 만 각각 {{, }} 로 변경하여 .format() 충돌을 방지
            base_prompt = self._escape_json_section_braces(base_prompt)
            
            # 기존 추천 장소 목록을 문자열로 변환
            if existing_places:
                previously_recommended_text = f"""
이미 추천된 장소들 (중복 금지):
{', '.join(existing_places)}

위 장소들과 중복되지 않는 새로운 장소만 추천해주세요."""
            else:
                previously_recommended_text = "첫 번째 추천이므로 제약 없이 최고의 장소들을 추천해주세요."
            
            # 프롬프트 변수 치환 (실제 Supabase 프롬프트 변수명에 맞게 매핑)
            dynamic_prompt = base_prompt.format(
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
    
    def _escape_json_section_braces(self, prompt_template: str) -> str:
        """프롬프트 내 '//-- 필수 JSON 출력 형식 --//' 이후의 중괄호를 이스케이프 처리

        - 구분자 이전 구간은 그대로 둔다.
        - 구분자 이후 구간에서 '{' -> '{{', '}' -> '}}' 로 치환한다.
        """
        try:
            delimiter = "//-- 필수 JSON 출력 형식 --//"
            idx = prompt_template.find(delimiter)
            if idx == -1:
                return prompt_template
            before = prompt_template[: idx + len(delimiter)]
            after = prompt_template[idx + len(delimiter) :]
            after = after.replace("{", "{{").replace("}", "}}")
            return before + after
        except Exception:
            # 문제 발생 시 원본을 그대로 반환하여 실패를 피함
            return prompt_template

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
                        places = await self.google_places.search_places(
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


# 전역 인스턴스
place_recommendation_service = PlaceRecommendationService()