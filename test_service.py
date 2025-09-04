#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import asyncio
sys.path.append('.')

from app.services.advanced_itinerary_service import AdvancedItineraryService
from app.schemas.itinerary import OptimizeRequest, PlaceData

async def test_service():
    print("=== Advanced Itinerary Service Test ===")
    
    service = AdvancedItineraryService()
    
    # 테스트 데이터
    test_places = [
        PlaceData(
            place_id='test1',
            name='Test Place 1',
            category='tourism',
            lat=37.5665,
            lng=126.9780,
            rating=4.5,
            address='Seoul, South Korea',
            description='Test place description'
        )
    ]
    
    test_request = OptimizeRequest(
        selected_places=test_places,
        language_code='ko',
        daily_start_time='09:00',
        daily_end_time='22:00',
        duration=2
    )
    
    print("Test starting: AdvancedItineraryService")
    try:
        result = await service.optimize_itinerary(test_request)
        print("✅ Test SUCCESS!")
        print(f"Result type: {type(result)}")
        if hasattr(result, 'travel_plan'):
            travel_plan = result.travel_plan
            if hasattr(travel_plan, 'days'):
                print(f"Daily plans count: {len(travel_plan.days) if travel_plan.days else 0}")
        return True
    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_service())
    print(f"\nTest result: {'PASS' if success else 'FAIL'}")