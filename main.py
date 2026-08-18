from datetime import datetime
import json
import requests
import pytz

# ==========================================
# CONFIGURATION
# ==========================================
CLOUDFLARE_WORKER_URL = "https://your-worker-name.your-subdomain.workers.dev/api/checklist"
API_SECRET_KEY = "YOUR_CLOUDFLARE_SECRET_KEY"

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
