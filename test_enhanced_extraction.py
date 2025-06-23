import asyncio
import json
from perplexity_events_extractor import DubaiEventsPerplexityExtractor

async def test_extraction():
    extractor = DubaiEventsPerplexityExtractor()
    
    # Test with a simple query to see enhanced field extraction
    result = await extractor.search_and_extract_events(
        'Dubai family events this weekend December 2025'
    )
    
    if result and 'events' in result and result['events']:
        events = result['events']
        print(f"Extracted {len(events)} events")
        first_event = events[0]
        
        # Check for enhanced fields
        enhanced_fields = [
            'social_media', 'quality_metrics', 'event_url', 'target_audience',
            'venue_type', 'event_type', 'indoor_outdoor', 'primary_category',
            'secondary_categories', 'ticket_links', 'contact_info'
        ]
        
        print("\n=== ENHANCED FIELDS CHECK ===")
        for field in enhanced_fields:
            value = first_event.get(field)
            has_data = value is not None and value != [] and value != {}
            print(f"{field}: {'✅ HAS DATA' if has_data else '❌ NO DATA'} - {str(value)[:100]}")
        
        print("\n=== SAMPLE EVENT DATA ===")
        print(json.dumps(first_event, indent=2, default=str)[:2000])
    else:
        print("No events extracted or extraction failed!")
        print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_extraction())