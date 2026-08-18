import os
import json
import requests
from datetime import datetime, timezone

CLOUDFLARE_WORKER_URL = os.getenv("CLOUDFLARE_WORKER_URL")
API_SECRET_KEY = os.getenv("API_SECRET_KEY")


def get_full_checklist_data():
    # --- ตัวอย่างการกำหนดค่าตัวแปรทดสอบการประมวลผลระบบ ---
    is_ny_session = True
    market_env = "Value Up"
    gex_type = "Negative Gamma (-GEX)"
    key_levels_done = True

    current_price, val_price, fib_level, m5_volume = 21050.0, 21100.0, 0.786, 22500
    has_absorption, is_bullish_close, has_imbalance, sl_valid = (
        True,
        True,
        True,
        True,
    )
    rr_ratio = 1.8  # >= 1.5R

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sections": [
            {
                "id": "sec1",
                "title": "📊 ส่วนที่ 1: ขั้นตอนก่อนตลาดเปิด (Pre-Market Preparation)",
                "subtitle": "วิเคราะห์สภาวะตลาดภาพใหญ่ ห้ามทำระหว่างราคาวิ่ง",
                "items": [
                    {
                        "topic": "1. สภาพคล่องรวม (Volume)",
                        "detail": "[เงื่อนไขเวลา]: ต้องเทรดเฉพาะช่วง 1 ชั่วโมงครึ่งแรกที่ตลาดนิวยอร์กเปิดทำการเท่านั้น (New York Open Session)",
                        "mt5": "Local Time / Session Indicator",
                        "tradingview": "Sessions (โดย LuxuryAlgo หรือ SpacemanITC)",
                        "pass": is_ny_session,
                        "result": "อยู่ในช่วงเทรดหลัก New York Open Session"
                        if is_ny_session
                        else "อยู่นอกช่วงเวลาเทรดหลัก",
                    },
                    {
                        "topic": "2. โครงสร้างตลาด (Environment)",
                        "detail": "[เงื่อนไขโครงสร้าง]: ตรวจสอบกราฟโครงสร้างราคาระดับสูง (1H หรือ 4H) ระบุแนวโน้มหลัก (Value Up / Value Down / Sideways)",
                        "mt5": "Market Structure Break (MSB) / กราฟเปล่า",
                        "tradingview": "Market Structure Break (MSB)",
                        "pass": market_env == "Value Up",
                        "result": f"โครงสร้างตลาดเป็น: {market_env} (เน้นฝั่ง Long)",
                    },
                    {
                        "topic": "3. สภาวะผันผวน (GEX Regime)",
                        "detail": "[เงื่อนไขความผันผวน]: เช็คค่า Gamma Exposure ผ่าน Naive GEX (+GEX = วิ่งในกรอบ / -GEX = เร่งความผันผวน)",
                        "mt5": "SpotGamma / Tanuki Trade (External)",
                        "tradingview": "Gamma Exposure Profile / Script เสียเงิน",
                        "pass": True,
                        "result": f"สภาวะตลาด: {gex_type} (ราคาเร่งความผันผวน วิ่งแรงและไกล)",
                    },
                    {
                        "topic": "4. ค้นหาแนวรับ-แนวต้านสำคัญ",
                        "detail": "[เงื่อนไขกรอบราคาหลัก]: มาร์กเส้นราคาสำคัญ Call Wall, Put Wall และ Gamma Flip Zone บนกราฟ",
                        "mt5": "มาร์กเส้นแนวนอนด้วยตนเอง (Horizontal Line)",
                        "tradingview": "มาร์กเส้นแนวนอนด้วยตนเอง ตามข้อมูลออปชันรายวัน",
                        "pass": key_levels_done,
                        "result": "มาร์กแนวรับ-แนวต้าน Call/Put Wall และ Gamma Flip เรียบร้อย",
                    },
                ],
            },
            {
                "id": "sec2",
                "title": "📍 ส่วนที่ 2: การคัดกรองหน้าเทรด (Setup & Location)",
                "subtitle": "กรณีสำหรับหน้าเทรดขาขึ้น (Value Up) เพื่อหาจังหวะ Long ในโซนราคาถูก",
                "items": [
                    {
                        "topic": "1. หลุดโซนมูลค่า (Out of Value)",
                        "detail": "[เงื่อนไขราคาถูก]: ราคาต้องร่วงหลุดต่ำกว่าเส้น Value Area Low (VAL) ของกรอบมูลค่าก่อนหน้า",
                        "mt5": "Market Profile / Volume Profile (มองหาเส้น VAL)",
                        "tradingview": "Volume Profile Visible Range (VPVR) / SVP",
                        "pass": current_price < val_price,
                        "result": f"ราคาปัจจุบัน ({current_price}) หลุดต่ำกว่า VAL ({val_price})",
                    },
                    {
                        "topic": "2. อยู่ในโซน Discount",
                        "detail": "[เงื่อนไขจุดพิกัด]: Fibonacci Retracement อยู่ภายในโซน Golden Pocket ระหว่าง 70.5% - 88.6%",
                        "mt5": "Fibonacci Retracement Tool (ระดับ 0.705, 0.788, 0.886)",
                        "tradingview": "Fib Retracement Tool (ติ๊กช่อง 0.705, 0.788, 0.886)",
                        "pass": 0.705 <= fib_level <= 0.886,
                        "result": f"ระดับ Fib อยู่ที่ {fib_level*100:.1f}% (อยู่ในโซน Discount)",
                    },
                    {
                        "topic": "3. ปริมาณหนาแน่น (Volume)",
                        "detail": "[เงื่อนไขพลังประมูล]: ในกราฟ MNQ แท่ง 5 นาที ต้องมีปริมาณสัญญาซื้อขายสะสมรวมกัน > 20,000 สัญญาขึ้นไป",
                        "mt5": "Tick Volume / Real Volume (เปิดแสดงบน MNQ/NQ)",
                        "tradingview": "Volume (อินดิเคเตอร์มาตรฐาน กราฟ CME เช่น MNQ1!)",
                        "pass": m5_volume >= 20000,
                        "result": f"Volume 5m สะสม {m5_volume:,} สัญญา (เกิน 20,000 สัญญา)",
                    },
                    {
                        "topic": "4. กฎเหล็กควบคุมความเสี่ยง",
                        "detail": "[เงื่อนไขยกเลิกแผน (Invalidation)]: หากเนื้อแท่งเทียนปิดหลุดทะลุแนว Fib 88.6% ให้ยกเลิกแผน Long ทั้งหมดทันที",
                        "mt5": "Fibonacci Retracement Tool (เฝ้าระวังระดับ 0.886)",
                        "tradingview": "Fib Retracement Tool (เฝ้าระวังระดับ 0.886)",
                        "pass": fib_level <= 0.886,
                        "result": "ราคายังทรงตัวได้ ไม่หลุดแนว Fib 88.6%",
                    },
                ],
            },
            {
                "id": "sec3",
                "title": "🕵️‍♂️ ส่วนที่ 3: สัญญาณยืนยันและการเข้าออเดอร์ (Confirmation & Entry)",
                "subtitle": "เปิดกราฟพฤติกรรมราคาเชิงลึกกรอบเวลา 5 นาที เพื่อหาจุดกดออเดอร์",
                "items": [
                    {
                        "topic": "1. สัญญาณซับแรงขาย (Absorption)",
                        "detail": "[เงื่อนไขดักจับรายใหญ่]: แท่ง 5m ทิ้งดิ่งมีไส้ล่างยาว บน Footprint เจอ POC รวมตัวด้านล่างพร้อม Negative Delta เข้มข้น",
                        "mt5": "ClusterDelta / OrderFlow Indicator",
                        "tradingview": "Order Flow / Footprint Chart",
                        "pass": has_absorption,
                        "result": "ตรวจพบ Buying Absorption มีการดักซับคำสั่งขายด้านล่าง",
                    },
                    {
                        "topic": "2. แรงซื้อคุมเกม (Dominance Shift)",
                        "detail": "[เงื่อนไขเปลี่ยนขั้วอำนาจ]: แท่งเทียนที่มี Absorption ต้องพลิกกลับมาปิดเป็นแท่งเข้ม/ปิดบวก (Bullish Close) ได้สำเร็จ",
                        "mt5": "เนื้อแท่งเทียนมาตรฐานบน MT5",
                        "tradingview": "เนื้อแท่งเทียนมาตรฐานบน TradingView",
                        "pass": is_bullish_close,
                        "result": "แท่งเทียนพลิกกลับมาปิดบวก (Bullish Close) ยืนยันฝั่งซื้อคุมเกม",
                    },
                    {
                        "topic": "3. สัญญาณเข้าทำ (Trigger Candle)",
                        "detail": "[เงื่อนไขกดปุ่มส่งคำสั่ง]: แท่งถัดมาย่อทำ Low สูงขึ้น (Fail Higher) + บน Footprint เกิด Buying Imbalance > 400%",
                        "mt5": "OrderFlow Imbalance / Footprint (มองหาตัวหนาเขียว)",
                        "tradingview": "Volume Imbalance / Footprint Chart",
                        "pass": has_imbalance,
                        "result": "เกิด Buying Imbalance > 400% ฝั่ง Ask เข้าเงื่อนไข Trigger Long",
                    },
                    {
                        "topic": "4. วางจุดตัดขาดทุน (Stop Loss)",
                        "detail": "[เงื่อนไขความเสี่ยง]: ตั้งระยะตัดขาดทุน (SL) ไว้อยู่ที่บริเวณใต้ปลายไส้เทียนของแท่ง Failed Sellers",
                        "mt5": "Crosshair Tool วัดระยะและวางราคา SL",
                        "tradingview": "Long Position Tool วัดระยะตัดขาดทุน",
                        "pass": sl_valid,
                        "result": "ตั้ง Stop Loss ใต้ปลายไส้เทียน Failed Sellers เรียบร้อย",
                    },
                ],
            },
            {
                "id": "sec4",
                "title": "🎯 ส่วนที่ 4: การบริหารจัดการและเป้าหมาย (Trade Management & Exit)",
                "subtitle": "การตั้งเป้าหมายทำกำไร คุมความเสี่ยง และเลื่อนจุดตัดขาดทุน",
                "items": [
                    {
                        "topic": "1. ตั้งเป้าหมายทำกำไร (TP)",
                        "detail": "[เงื่อนไขทางออก]: ตั้งเป้าทำกำไรที่แนว Swing High เดิม หรือบริเวณที่มีออเดอร์ฝั่งขายตั้งรอหนาแน่นบน Orderbook",
                        "mt5": "Horizontal Line / ดูจุดยอด Swing High ใน 15m/1H",
                        "tradingview": "Horizontal Line / อินดิเคเตอร์ ZigZag",
                        "pass": True,
                        "result": "กำหนดจุด TP ไว้ที่แนว Swing High หลักเดิมเรียบร้อย",
                    },
                    {
                        "topic": "2. อัตราความคุ้มค่า (R:R Ratio)",
                        "detail": "[เงื่อนไขความคุ้มค่า]: ระยะ TP เทียบกับระยะ SL ต้องมีสัดส่วนขั้นต่ำอยู่ที่ 1.5R ถึง 2R ขึ้นไป",
                        "mt5": "EA Risk Manager / วัดระยะพอยท์ด้วย Crosshair",
                        "tradingview": "Long Position Tool คำนวณ R:R Ratio อัตโนมัติ",
                        "pass": rr_ratio >= 1.5,
                        "result": f"อัตรา R:R อยู่ที่ {rr_ratio}R (ผ่านเกณฑ์ขั้นต่ำ 1.5R)",
                    },
                    {
                        "topic": "3. การเลื่อนจุดคุ้มทุน (Trailing)",
                        "detail": "[เงื่อนไขล็อกกำไร]: หากราคาพุ่งกลับเข้า Value Area ได้ + โชว์แรงซื้อดันต่อเนื่อง ให้ Trail Stop มาบังทุน",
                        "mt5": "Trailing Stop ฟีเจอร์มาตรฐานของ MT5",
                        "tradingview": "Price Note เลื่อนเส้น Stop Loss แบบ Manual",
                        "pass": True,
                        "result": "เตรียมแผน Trailing Stop เลื่อนบังทุนเมื่อราคาเข้าโซน Value",
                    },
                    {
                        "topic": "4. สัญญาณเตือนฝั่งตรงข้าม (Red Flag)",
                        "detail": "[เงื่อนไขหนีเอาตัวรอด]: หากเกิด Buying Absorption ใต้แนว Value Area ให้รีบขยับ SL บังทุนหรือปิดออเดอร์ทันที",
                        "mt5": "ClusterDelta / OrderFlow ดู Bid หนักแต่ราคาไม่พุ่ง",
                        "tradingview": "สังเกตสัญญาณ Imbalance ฝั่งตรงข้าม บน Footprint",
                        "pass": True,
                        "result": "เฝ้าระวัง Red Flag สัญญาณติดดอยฝั่งซื้อพร้อมคัททันที",
                    },
                ],
            },
        ],
    }


def main():
    payload = get_full_checklist_data()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_SECRET_KEY}",
    }

    try:
        res = requests.post(
            CLOUDFLARE_WORKER_URL, json=payload, headers=headers
        )
        if res.status_code == 200:
            print("✅ ส่งข้อมูลเช็คลิสต์ทั้ง 4 ส่วนไปยัง Cloudflare สำเร็จแล้ว!")
        else:
            print(f"❌ ส่งข้อมูลล้มเหลว: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")


if __name__ == "__main__":
    main()
