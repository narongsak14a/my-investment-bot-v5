from datetime import datetime
import json
import requests
import pytz

# ==========================================
# CONFIGURATION
# ==========================================
import os

# ดึงค่า URL และ Token จาก GitHub Secrets ผ่าน Environment Variables
CLOUDFLARE_WORKER_URL = os.getenv("CLOUDFLARE_WORKER_URL")
API_SECRET_KEY = os.getenv("CLOUDFLARE_AUTH_TOKEN")

# ==========================================
# 1. CHECKLIST LOGIC FUNCTIONS
# ==========================================

def check_ny_session():
    """1. ตรวจสอบเวลาช่วง New York Open (8:00 AM - 9:30 AM EST)"""
    ny_tz = pytz.timezone('America/New_York')
    ny_time = datetime.now(ny_tz)
    
    # คำนวณเวลาในนาทีตั้งแต่เริ่มวัน
    minutes_since_midnight = ny_time.hour * 60 + ny_time.minute
    ny_open_start = 8 * 60      # 08:00 AM
    ny_open_end = 9 * 60 + 30   # 09:30 AM
    
    is_active = ny_open_start <= minutes_since_midnight <= ny_open_end
    
    return {
        "status": "PASS" if is_active else "FAIL",
        "current_ny_time": ny_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "detail": "อยู่ในช่วง 1.5 ชม. แรกที่ตลาดนิวยอร์กเปิดทำการ" if is_active else "อยู่นอกช่วงเวลาเทรดหลัก (เสี่ยงสภาพคล่องต่ำ/ไซด์เวย์)"
    }

def check_market_structure():
    """2. จำลองการวิเคราะห์โครงสร้างตลาด (1H / 4H)"""
    # หมายเหตุ: ในระบบจริงสามารถดึงราคา High/Low จาก TradingView/MT5 API มาคำนวณ HH/HL หรือ LL/LH
    # ตัวอย่างคืนค่าโครงสร้างล่าสุด
    structure_type = "Value Up"  # Value Up, Value Down, หรือ Sideways
    
    bias_map = {
        "Value Up": "เน้นฝั่ง Long เท่านั้น (ราคายก High/Low)",
        "Value Down": "เน้นฝั่ง Short เท่านั้น (ราคาทำ Low/High ต่ำลง)",
        "Sideways": "เน้นเล่นในกรอบ (ราคาวิ่งสะสมกรอบมูลค่าเดิม)"
    }
    
    return {
        "structure": structure_type,
        "recommendation": bias_map.get(structure_type, "N/A")
    }

def check_gex_regime():
    """3. เช็คสภาวะผันผวน (GEX Regime)"""
    # ดึงข้อมูลจาก External API เช่น Tanuki / SpotGamma หรือคำนวณ Naive GEX
    gex_value = -125000  # ตัวอย่างค่า Negative GEX
    
    if gex_value > 0:
        regime = "Positive Gamma (+GEX)"
        behavior = "ซับความผันผวน ตลาดวิ่งในกรอบแคบ เบรคหลอกบ่อย (ห้ามเล่น Breakout)"
    else:
        regime = "Negative Gamma (-GEX)"
        behavior = "เร่งความผันผวน ราคาจะวิ่งแรงและเร็ว (เหมาะแก่การเล่นตามเทรนด์)"
        
    return {
        "gex_value": gex_value,
        "regime": regime,
        "behavior": behavior
    }

def fetch_key_levels():
    """4. ค้นหาแนวรับ-แนวต้านสำคัญจาก Option Market"""
    # ตัวอย่างค่าที่มาร์กไว้จาก Option Data
    return {
        "call_wall": 2750.00,       # แนวต้านสูงสุด
        "put_wall": 2680.00,        # แนวรับต่ำสุด
        "gamma_flip_zone": 2715.00  # เส้นแบ่งเขตแดนความผันผวน
    }

def check_setup_value_up(current_price, val_price, fib_level, M5_volume):
    """
    ส่วนที่ 2: การคัดกรองหน้าเทรด (Setup & Location) - กรณี Value Up (Long)
    """
    # 1. หลุดโซนมูลค่า (Out of Value): ราคาอยู่ต่ำกว่า VAL
    is_out_of_value = current_price < val_price
    
    # 2. อยู่ในโซน Discount: Fib อยู่ระหว่าง 70.5% - 88.6% (0.705 - 0.886)
    is_discount_zone = 0.705 <= fib_level <= 0.886
    
    # 3. ปริมาณหนาแน่น (Volume 5m): สะสม > 20,000 สัญญา
    is_high_volume = M5_volume >= 20000
    
    # 4. กฎเหล็กควบคุมความเสี่ยง (Invalidation): ปิดหลุด Fib 88.6% (0.886)
    is_invalidated = fib_level > 0.886

    # สรุปผลการคัดกรอง
    if is_invalidated:
        setup_status = "INVALIDATED"
        recommendation = "❌ ยกเลิกแผน Long ทันที! ราคาปิดหลุด Fib 88.6% โครงสร้างฝั่งซื้อเสียหาย"
    elif is_out_of_value and is_discount_zone and is_high_volume:
        setup_status = "PASS"
        recommendation = "✅ เข้าเงื่อนไข Long ครบทุกข้อ! สามารถพิจารณาเข้าเทรดได้"
    else:
        setup_status = "WAIT"
        recommendation = "⏳ เงื่อนไขยังไม่ครบตามแผน รอจังหวะเพิ่มเติม"

    return {
        "status": setup_status,
        "recommendation": recommendation,
        "checklist": {
            "1_out_of_value": {
                "pass": is_out_of_value,
                "detail": f"ราคาปัจจุบัน ({current_price}) หลุดต่ำกว่า VAL ({val_price})" if is_out_of_value else f"ราคายังไม่หลุด VAL ({val_price})"
            },
            "2_discount_zone": {
                "pass": is_discount_zone,
                "detail": f"ระดับ Fib อยู่ที่ {fib_level*100:.1f}% (อยู่ในโซน 70.5% - 88.6%)" if is_discount_zone else f"ระดับ Fib อยู่ที่ {fib_level*100:.1f}% (ไม่อยู่ในโซน Discount)"
            },
            "3_volume_m5": {
                "pass": is_high_volume,
                "detail": f"Volume 5m สะสม {M5_volume:,} สัญญา (มากกว่า 20,000)" if is_high_volume else f"Volume 5m สะสม {M5_volume:,} สัญญา (ต่ำกว่า 20,000 สัญญา ตลาดหมดพลัง)"
            },
            "4_invalidation_rule": {
                "is_invalidated": is_invalidated,
                "detail": "ราคาหลุด 88.6% ห้ามช้อนซื้อเด็ดขาด" if is_invalidated else "ราคายังปลอดภัย ไม่หลุดระดับ 88.6%"
            }
        }
    }


# ==========================================
# 2. RUN CHECKLIST & SEND TO CLOUDFLARE
# ==========================================

def main():
    print("📋 กำลังรวบรวมข้อมูลเช็คลิสต์ก่อนตลาดเปิด...")
    
    # รวมข้อมูลตามแผนการเทรด
    checklist_payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "section": "ส่วนที่ 1: ขั้นตอนก่อนตลาดเปิด (Pre-Market Preparation)",
        "items": {
            "1_volume_session": check_ny_session(),
            "2_environment": check_market_structure(),
            "3_gex_regime": check_gex_regime(),
            "4_key_levels": fetch_key_levels()
        }
    }

    # ส่งออกไปยัง Cloudflare Worker
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_SECRET_KEY}"
    }

    try:
        response = requests.post(CLOUDFLARE_WORKER_URL, json=checklist_payload, headers=headers)
        if response.status_code in [200, 201]:
            print("✅ ส่งข้อมูลเช็คลิสต์ไปยัง Cloudflare Worker เรียบร้อยแล้ว!")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"❌ เกิดข้อผิดพลาดในการส่งข้อมูล: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ ไม่สามารถเชื่อมต่อกับ Cloudflare Worker ได้: {str(e)}")

if __name__ == "__main__":
    main()
