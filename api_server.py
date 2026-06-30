"""
班级签到系统 - API 服务器
=========================
基于 FastAPI + YOLOv8 的人员检测和签到 API。

支持:
    - POST /detect_persons: 上传图片检测人数
    - GET /records: 获取签到记录
    - POST /records: 添加签到记录
"""

import json
import base64
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO

app = FastAPI(title="班级签到系统 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RECORDS_FILE = Path("attendance_records.json")
PERSON_CLASS_ID = 0
model = YOLO("yolov8n.pt")


def load_records() -> list[dict]:
    if not RECORDS_FILE.exists():
        return []
    try:
        with open(RECORDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_records(records: list[dict]):
    with open(RECORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


@app.post("/detect_persons")
async def detect_persons(file: UploadFile = File(...)):
    """上传图片进行人员检测，返回标注后的图片和人数。"""
    img_bytes = await file.read()
    np_arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    results = model(img, classes=[PERSON_CLASS_ID], conf=0.35)
    annotated = img.copy()
    count = 0

    for box in results[0].boxes:
        conf = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        count += 1
        color = (0, int(180 + conf * 48), int(255 - conf * 48))
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        label = f"person {conf:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 8, y1), color, -1)
        cv2.putText(annotated, label, (x1 + 4, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    _, buffer = cv2.imencode(".jpg", annotated)
    img_b64 = base64.b64encode(buffer).decode("utf-8")

    return {"count": count, "img_base64": img_b64}


@app.get("/records")
async def get_records():
    """获取所有签到记录。"""
    return {"records": load_records()}


@app.post("/records")
async def add_record(class_name: str, expected: int, actual: int, note: str = ""):
    """添加一条签到记录。"""
    records = load_records()
    records.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "class_name": class_name,
        "expected": expected,
        "actual": actual,
        "absent": max(0, expected - actual),
        "rate": round(actual / expected * 100, 1) if expected > 0 else 0,
        "note": note,
    })
    save_records(records)
    return {"status": "ok", "total": len(records)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000)
