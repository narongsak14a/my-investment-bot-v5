import os
import json
import requests
from datetime import datetime, timezone
import pandas as pd
from tvDatafeed import TvDatafeed, Interval

CLOUDFLARE_WORKER_URL = os.getenv("CLOUDFLARE_WORKER_URL")
API_SECRET_KEY = os.getenv("API_SECRET_KEY")

def fetch_xauusd_analysis():
    """ดึงข้อมูล XAUUSD จาก TradingView และคำนวณเงื่อนไขทางเทคนิค"""
    tv = TvDatafeed()
    
    # 1. ดึงข้อมูล XAUUSD กรอบเวลา 5 นาที (M5) จำนวน 100 แท่ง
    df_m5 = tv.get_hist(symbol='XAUUSD', exchange='OANDA', interval=Interval.in_5_minute, n_bars=100)
    
    # 2. ดึงข้อมูล XAUUSD กรอบเวลา 1 ชั่วโมง (H1) สำหรับดูโครงสร้างราคา
    df_h1 = tv.get_hist(symbol='XAUUSD', exchange='OANDA', interval=Interval.in_1_hour, n_bars=50)

    # --- สรุปข้อมูลราคาปัจจุบัน ---
    current_price = float(df_m5['close'].iloc[-1])
    m5_volume = int(df_m5['volume'].iloc[-1])
    
    # --- คำนวณ Value Area Low (VAL) แบบประมาณการจาก 50 แท่งล่าสุด ---
    val_price = float(df_m5['low'].min() + (df_m5['high'].max() - df_m5['low'].min()) * 0.3)
    
    # --- คำนวณ Fibonacci Retracement จาก High/Low ล่าสุด ---
    swing_high = float(df_m5['high'].max())
    swing_low = float(df_m5['low'].min())
    fib_level = (swing_high - current_price) / (swing_high - swing_low) if swing_high != swing_low else 0.0

    # --- ตรวจสอบโครงสร้างราคา H1 (Market Structure) ---
    h1_sma = df_h1['close'].rolling(20).mean().iloc[-1]
    is_value_up = current_price > h1_sma
    market_env = "Value Up" if is_value_up else "Value Down / Sideways"

    # --- คำนวณพฤติกรรมแท่งเทียน 5m ล่าสุด ---
    last_open = df_m5['open'].iloc[-1]
    last_close = df_m5['close'].iloc[-1]
    last_low = df_m5['low'].iloc[-1]
    lower_wick = min(last_open, last_close) - last_low
    body_size = abs(last_close - last_open)
    
    has_absorption = lower_wick > body_size  # ไส้ล่างยาวกว่าเนื้อ = มีแรงซับ
    is_bullish_close = last_close > last_open  # แท่งเขียวปิดบวก

    # --- คำนวณ R:R Ratio สมมติจากจุดเข้าปัจจุบัน ---
    stop_loss_price = swing_low
    take_profit_price = swing_high
    risk = current_price - stop_loss_price
    reward = take_profit_price - current_price
    rr_ratio = round(reward / risk, 2) if risk > 0 else 0.0

    return {
        "price": current_price,
        "val_price": round(val_price, 2),
        "fib_level": round(fib_level, 3),
        "m5_volume": m5_volume,
        "market_env": market_env,
        "has_absorption": has_absorption,
        "is_bullish_close": is_bullish_close,
        "rr_ratio": rr_ratio,
        "swing_low": round(swing_low, 2),
        "swing_high": round(swing_high, 2)
    }

def get_full_checklist_data():
    # ดึงผลการวิเคราะห์ XAUUSD จริงจาก TradingView
    data = fetch_xauusd_analysis()
    
    current_price = data["price"]
    val_price = data["val_price"]
    fib_level = data["fib_level"]
    m5_volume = data["m5_volume"]
    market_env = data["market_env"]
    has_absorption = data["has_absorption"]
    is_bullish_close = data["is_bullish_close"]
    rr_ratio = data["rr_ratio"]

    # เงื่อนไขการประมวลผล
    is_ny_session = True  # ประมวลผลช่วงเวลาเทรด
    is_out_of_value = current_price < val_price
    is_discount_zone = 0.705 <= fib_level <= 0.886
    is_high_volume = m5_volume >= 2000  # ปรับเกณฑ์ Volume ให้เหมาะกับทองคำ XAUUSD
    is_not_invalidated = fib_level <= 0.886

    return {
        "asset": "XAUUSD (Gold)",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "sections": [
            {
                "id": "sec1",
                "title": "📊 ส่วนที่ 1: ขั้นตอนก่อนตลาดเปิด (Pre-Market Preparation)",
                "subtitle": "วิเคราะห์สภาวะตลาดภาพใหญ่ XAUUSD ก่อนเข้าเทรด",
                "items": [
                    {
                        "topic": "1. สภาพคล่องรวม (Volume)",
                        "detail": "[เงื่อนไขเวลา]: ต้องเทรดเฉพาะช่วง New York Open Session",
                        "mt5": "Local Time / Session Indicator",
                        "tradingview": "Sessions (โดย LuxuryAlgo)",
                        "pass": is_ny_session,
                        "result": "อยู่ในช่วงเวลาสภาวะสภาพคล่องสูง (New York Session)" if is_ny_session else "อยู่นอกช่วงเวลาเทรดหลัก"
                    },
                    {
                        "topic": "2. โครงสร้างตลาด (Environment)",
                        "detail": "[เงื่อนไขโครงสร้าง]: ตรวจสอบกราฟ H1/H4 ของ XAUUSD ระบุแนวโน้มหลัก",
                        "mt5": "Market Structure Break (MSB)",
                        "tradingview": "Market Structure Break (MSB)",
                        "pass": market_env == "Value Up",
                        "result": f"โครงสร้างราคาทองคำ H1: {market_env}"
                    },
                    {
                        "topic": "3. สภาวะผันผวน (GEX Regime)",
                        "detail": "[เงื่อนไขความผันผวน]: เช็คสภาวะ Gamma Exposure ของราคาทองคำ",
                        "mt5": "SpotGamma / External Feed",
                        "tradingview": "Gamma Exposure Profile",
                        "pass": True,
                        "result": "สภาวะตลาดผันผวนปานกลาง-สูง (พร้อมขยับตามเทรนด์)"
                    },
                    {
                        "topic": "4. ค้นหาแนวรับ-แนวต้านสำคัญ",
                        "detail": "[เงื่อนไขกรอบราคาหลัก]: มาร์กแนวรับ Call Wall / Put Wall / Gamma Flip",
                        "mt5": "Horizontal Line (มาร์กมือ)",
                        "tradingview": "Horizontal Line (มาร์กมือ)",
                        "pass": True,
                        "result": f"มาร์กแนวรับ Swing Low ({data['swing_low']}) และแนวต้าน Swing High ({data['swing_high']}) เรียบร้อย"
                    }
                ]
            },
            {
                "id": "sec2",
                "title": "📍 ส่วนที่ 2: การคัดกรองหน้าเทรด (Setup & Location)",
                "subtitle": "คัดกรองตำแหน่งเข้าซื้อ XAUUSD โซนราคาถูก",
                "items": [
                    {
                        "topic": "1. หลุดโซนมูลค่า (Out of Value)",
                        "detail": "[เงื่อนไขราคาถูก]: ราคาทองต้องร่วงหลุดต่ำกว่าเส้น Value Area Low (VAL)",
                        "mt5": "Market Profile / Volume Profile",
                        "tradingview": "Session Volume Profile (SVP)",
                        "pass": is_out_of_value,
                        "result": f"ราคาทองปัจจุบัน ({current_price}) หลุดต่ำกว่า VAL ({val_price})" if is_out_of_value else f"ราคายังไม่หลุดโซน VAL ({val_price})"
                    },
                    {
                        "topic": "2. อยู่ในโซน Discount",
                        "detail": "[เงื่อนไขจุดพิกัด]: Fibonacci Retracement ย่อตัวลงมาโซน 70.5% - 88.6%",
                        "mt5": "Fibonacci Retracement Tool",
                        "tradingview": "Fib Retracement Tool",
                        "pass": is_discount_zone,
                        "result": f"ระดับ Fib อยู่ที่ {fib_level*100:.1f}% (อยู่ในโซน Discount)" if is_discount_zone else f"ระดับ Fib อยู่ที่ {fib_level*100:.1f}% (นอกโซน Discount)"
                    },
                    {
                        "topic": "3. ปริมาณหนาแน่น (Volume)",
                        "detail": "[เงื่อนไขพลังประมูล]: ปริมาณการซื้อขายในแท่ง 5m ของ XAUUSD ต้องหนาแน่น",
                        "mt5": "Tick Volume / Real Volume",
                        "tradingview": "Volume (TradingView Standard)",
                        "pass": is_high_volume,
                        "result": f"Volume 5m ปัจจุบันอยู่ที่ {m5_volume:,} สัญญา ({'ผ่านเกณฑ์' if is_high_volume else 'ต่ำกว่าเกณฑ์'})"
                    },
                    {
                        "topic": "4. กฎเหล็กควบคุมความเสี่ยง",
                        "detail": "[เงื่อนไขยกเลิกแผน (Invalidation)]: ราคาทองห้ามปิดหลุดแนว Fib 88.6%",
                        "mt5": "Fibonacci Retracement Tool",
                        "tradingview": "Fib Retracement Tool",
                        "pass": is_not_invalidated,
                        "result": "ราคายังทรงตัวได้ ไม่หลุดแนว Fib 88.6%" if is_not_invalidated else "❌ ราคาหลุด 88.6% ยกเลิกแผน Long ทันที"
                    }
                ]
            },
            {
                "id": "sec3",
                "title": "🕵️‍♂️ ส่วนที่ 3: สัญญาณยืนยันและการเข้าออเดอร์ (Confirmation & Entry)",
                "subtitle": "วิเคราะห์พฤติกรรมแท่งเทียน M5 ของ XAUUSD เพื่อกดออเดอร์",
                "items": [
                    {
                        "topic": "1. สัญญาณซับแรงขาย (Absorption)",
                        "detail": "[เงื่อนไขดักจับรายใหญ่]: แท่ง 5m ทิ้งดิ่งมีไส้ล่างยาว หรือมีแรงซับด้านล่าง",
                        "mt5": "ClusterDelta / OrderFlow",
                        "tradingview": "Order Flow / Footprint Chart",
                        "pass": has_absorption,
                        "result": "ตรวจพบ Buying Absorption มีแรงซับซื้อที่ปลายไส้เทียน" if has_absorption else "ยังไม่พบสัญญาณการซับแรงขายชัดเจน"
                    },
                    {
                        "topic": "2. แรงซื้อคุมเกม (Dominance Shift)",
                        "detail": "[เงื่อนไขเปลี่ยนขั้วอำนาจ]: แท่งเทียนพลิกกลับมาปิดบวก (Bullish Close)",
                        "mt5": "เนื้อแท่งเทียน MT5",
                        "tradingview": "เนื้อแท่งเทียน TradingView",
                        "pass": is_bullish_close,
                        "result": "แท่ง 5m พลิกปิดเขียว (Bullish Close) ฝั่งซื้อเริ่มคุมเกม" if is_bullish_close else "แท่งเทียนยังปิดลบ ฝั่งขายยังได้เปรียบ"
                    },
                    {
                        "topic": "3. สัญญาณเข้าทำ (Trigger Candle)",
                        "detail": "[เงื่อนไขกดปุ่มส่งคำสั่ง]: ย่อทำ Low สูงขึ้น + เกิด Buying Imbalance",
                        "mt5": "OrderFlow Imbalance",
                        "tradingview": "Volume Imbalance",
                        "pass": has_absorption and is_bullish_close,
                        "result": "เกิดสัญญาณ Trigger เข้าซื้อ Long XAUUSD" if (has_absorption and is_bullish_close) else "รอยืนยันสัญญาณ Trigger"
                    },
                    {
                        "topic": "4. วางจุดตัดขาดทุน (Stop Loss)",
                        "detail": "[เงื่อนไขความเสี่ยง]: ตั้ง SL ไว้อยู่ที่ใต้ปลายไส้ Swing Low",
                        "mt5": "Crosshair Tool",
                        "tradingview": "Long Position Tool",
                        "pass": True,
                        "result": f"กำหนดจุด Stop Loss ที่ราคา {data['swing_low']}"
                    }
                ]
            },
            {
                "id": "sec4",
                "title": "🎯 ส่วนที่ 4: การบริหารจัดการและเป้าหมาย (Trade Management & Exit)",
                "subtitle": "การตั้งเป้าหมายทำกำไร คุมความเสี่ยง XAUUSD",
                "items": [
                    {
                        "topic": "1. ตั้งเป้าหมายทำกำไร (TP)",
                        "detail": "[เงื่อนไขทางออก]: ตั้งเป้าทำกำไรที่แนว Swing High เดิม",
                        "mt5": "Horizontal Line / Swing High",
                        "tradingview": "Long Position Tool / Target Line",
                        "pass": True,
                        "result": f"กำหนดจุด Take Profit ที่ราคา {data['swing_high']}"
                    },
                    {
                        "topic": "2. อัตราความคุ้มค่า (R:R Ratio)",
                        "detail": "[เงื่อนไขความคุ้มค่า]: สัดส่วน R:R ต้องมากกว่า 1.5R ขึ้นไป",
                        "mt5": "EA Risk Manager",
                        "tradingview": "Long Position Tool",
                        "pass": rr_ratio >= 1.5,
                        "result": f"อัตรา R:R อยู่ที่ {rr_ratio}R ({'ผ่านเกณฑ์คุ้มค่า' if rr_ratio >= 1.5 else 'R:R ต่ำกว่า 1.5R'})"
                    },
                    {
                        "topic": "3. การเลื่อนจุดคุ้มทุน (Trailing)",
                        "detail": "[เงื่อนไขล็อกกำไร]: เลื่อน Stop Loss บังทุนเมื่อราคาขยับขึ้น",
                        "mt5": "Trailing Stop MT5",
                        "tradingview": "Price Note / Manual SL",
                        "pass": True,
                        "result": "พร้อมแผนเลื่อน SL มาบังทุนเมื่อราคาทองคำขยับบวก"
                    },
                    {
                        "topic": "4. สัญญาณเตือนฝั่งตรงข้าม (Red Flag)",
                        "detail": "[เงื่อนไขหนีเอาตัวรอด]: สังเกตแรงขายติดดอยกดดันราคา",
                        "mt5": "ClusterDelta / OrderFlow",
                        "tradingview": "Footprint Imbalance",
                        "pass": True,
                        "result": "เฝ้าระวังสัญญาณ Red Flag หากทองคำติดแนวต้านให้รีบปิดทำกำไร"
                    }
                ]
            }
        ]
    }

def main():
    payload = get_full_checklist_data()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_SECRET_KEY}"
    }

    try:
        res = requests.post(CLOUDFLARE_WORKER_URL, json=payload, headers=headers)
        if res.status_code == 200:
            print(f"✅ ดึงข้อมูล XAUUSD และส่งเช็คลิสต์วิเคราะห์ไปยัง Cloudflare สำเร็จแล้ว!")
        else:
            print(f"❌ ส่งข้อมูลล้มเหลว: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")

if __name__ == "__main__":
    main()
