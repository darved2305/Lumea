"""
Quick test of Grok Medicine Service
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.grok_medicine_service import GrokMedicineService

async def test_grok():
    print("🧪 Testing Grok Medicine Service\n")
    
    grok = GrokMedicineService()
    
    # Test 1: Parse medicine
    print("📝 Test 1: Parsing 'Paracetamol 500mg'...")
    try:
        result = await grok.parse_medicine("Paracetamol 500mg")
        print(f"✅ Parsed: {result.brand_name}")
        print(f"   Salts: {result.salts}")
        print(f"   Strength: {result.strength}")
        print(f"   Confidence: {result.confidence}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")
    
    # Test 2: Find alternatives
    print("🔍 Test 2: Finding alternatives for 'Crocin'...")
    try:
        result = await grok.get_alternatives_for_text("Crocin")
        print(f"✅ Found {result['count']} alternatives")
        print(f"   Match level: {result['match_level']}")
        
        if result['alternatives']:
            print("\n   Top 3 alternatives:")
            for alt in result['alternatives'][:3]:
                jan_badge = "🏥 Jan Aushadhi" if alt.get('is_jan_aushadhi') else ""
                print(f"   • {alt['brand_name']} - ₹{alt['price_mrp']} {jan_badge}")
                print(f"     Match: {int(alt['match_score']*100)}% - {', '.join(alt['match_reason'][:2])}")
        
        print(f"\n   Notes:")
        for note in result['notes']:
            print(f"   {note}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_grok())
