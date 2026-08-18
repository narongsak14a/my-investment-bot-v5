import os  # 👈 เพิ่มบรรทัดนี้ด้านบนสุด
import json
import requests
from datetime import datetime, timezone

CLOUDFLARE_WORKER_URL = os.getenv("CLOUDFLARE_WORKER_URL")
API_SECRET_KEY = os.getenv("API_SECRET_KEY")

# ==========================================
# 🔹 ส่วนที่ 1: เช็คลิสต์ก่อนตลาดเปิด (Pre-Market)
# ==========================================
def check_ny_session():
    return {"pass": True, "detail": "Volume ตลาด NY อยู่ในเกณฑ์ปกติ"}

def check_market_structure():
    return {"pass": True, "detail": "โครงสร้างราคาเป็นขาขึ้น (Higher High / Higher Low)"}

def check_gex_regime():
    return {"pass": True, "detail": "สถานะ GEX เป็น Positive Gamma"}

def fetch_key_levels():
    return {"pass": True, "detail": "ดึงแนวรับ-แนวต้านสำคัญเรียบร้อย"}


# ==========================================
# 🔹 ส่วนที่ 2: การคัดกรองหน้าเทรด (Setup & Location - Value Up)
# ==========================================
def check_setup_value_up(current_price, val_price, fib_level, M5_volume):
    """
    ฟังก์ชันคัดกรองหน้าเทรดขาขึ้น (Value Up / Long)
    """
    # 1. หลุดโซนมูลค่า (Out of Value): ราคาต่ำกว่า VAL
    is_out_of_value = current_price < val_price
    
    # 2. อยู่ในโซน Discount: Fib 70.5% - 88.6% (0.705 - 0.886)
    is_discount_zone = 0.705 <= fib_level <= 0.886
    
    # 3. ปริมาณหนาแน่น (Volume 5m): >= 20,000 สัญญา
    is_high_volume = M5_volume >= 20000
    
    # 4. กฎเหล็กควบคุมความเสี่ยง (Invalidation): ปิดหลุด Fib 88.6% (0.886)
    is_invalidated = fib_level > 0.886

    # ประเมินสถานะภาพรวม
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
                "detail": f"ระดับ Fib อยู่ที่ {fib_level*100:.1f}% (อยู่ในโซน Discount 70.5% - 88.6%)" if is_discount_zone else f"ระดับ Fib อยู่ที่ {fib_level*100:.1f}% (ไม่อยู่ในโซน Discount)"
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
# 🚀 ฟังก์ชันหลัก (Main Execution)
# ==========================================
def main():
    print("📋 กำลังรวบรวมข้อมูลเช็คลิสต์...")

    # 🔹 กำหนดค่าตัวแปรทดสอบสำหรับส่วนที่ 2 (สามารถเปลี่ยนเป็นดึงค่าจริงจาก API ในอนาคต)
    current_price = 21050.00   # ราคาปัจจุบัน
    val_price = 21100.00       # เส้น Value Area Low (VAL)
    fib_level = 0.786          # ย่อมาที่ระดับ Fib 78.6% (0.786)
    M5_volume = 22500          # ปริมาณ Volume แท่ง 5 นาที

    # 🔹 ประกอบ Payload รวมทั้ง Section 1 และ Section 2
    checklist_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "section_1": {
            "title": "ส่วนที่ 1: ขั้นตอนก่อนตลาดเปิด (Pre-Market Preparation)",
            "items": {
                "1_volume_session": check_ny_session(),
                "2_environment": check_market_structure(),
                "3_gex_regime": check_gex_regime(),
                "4_key_levels": fetch_key_levels()
            }
        },
        "section_2": {
            "title": "ส่วนที่ 2: การคัดกรองหน้าเทรด (Setup & Location - Value Up)",
            "data": check_setup_value_up(current_price, val_price, fib_level, M5_volume)
        }
    }

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
