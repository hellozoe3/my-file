"""
班级签到系统
============
基于 Streamlit + YOLOv8 的班级签到应用。
支持上传照片检测和摄像头实时监控两种模式。

功能:
    - 上传教室照片自动识别人数
    - 摄像头实时人形检测与人数统计
    - 应到人数 vs 实到人数对比记录
    - 签到历史记录持久化存储

环境安装:
    pip install streamlit opencv-python-headless ultralytics numpy pillow

启动方式:
    streamlit run app.py --server.address 0.0.0.0 --server.port 8501
"""

import json
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import streamlit as st
import pandas as pd
from ultralytics import YOLO

# ── 页面配置 ──────────────────────────────
st.set_page_config(
    page_title="班级签到系统",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 持久化文件路径 ──────────────────────────
RECORDS_FILE = Path("attendance_records.json")

# ── CSS 样式 ──────────────────────────────
st.markdown("""
<style>
    .sidebar-title {
        font-size: 18px;
        font-weight: 700;
        color: #f0f2f6;
        margin-bottom: 4px;
    }
    .sidebar-subtitle {
        font-size: 12px;
        color: #9aa0a6;
        margin-bottom: 16px;
    }
    .stat-card {
        padding: 16px 20px;
        border-radius: 10px;
        text-align: center;
        color: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    .stat-card .label {
        font-size: 13px;
        opacity: 0.85;
        letter-spacing: 0.5px;
    }
    .stat-card .value {
        font-size: 32px;
        font-weight: 700;
        line-height: 1.3;
    }
    .stat-card .value.absent { color: #ff6b6b; }
    .stat-card .value.present { color: #51cf66; }
    .rate-badge {
        display: inline-block;
        padding: 2px 12px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 600;
    }
    .rate-badge.high  { background: #216e39; color: #b2f2bb; }
    .rate-badge.medium { background: #7a6200; color: #ffe066; }
    .rate-badge.low   { background: #862e2e; color: #ffc9c9; }
</style>
""", unsafe_allow_html=True)


# ── 持久化存储工具 ──────────────────────────

def load_records() -> list[dict]:
    """从 JSON 文件加载签到记录。"""
    if not RECORDS_FILE.exists():
        return []
    try:
        with open(RECORDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_records(records: list[dict]):
    """保存签到记录到 JSON 文件。"""
    with open(RECORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def add_record(class_name: str, expected: int, actual: int, note: str = ""):
    """添加一条签到记录。"""
    records = load_records()
    records.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "class_name": class_name,
        "expected": expected,
        "actual": actual,
        "absent": expected - actual if expected >= actual else 0,
        "rate": round(actual / expected * 100, 1) if expected > 0 else 0,
        "note": note,
    })
    save_records(records)
    return records


# ── 模型加载 ──────────────────────────────
@st.cache_resource
def load_model():
    return YOLO("yolov8n.pt")


# ── 人员检测 ──────────────────────────────
PERSON_CLASS_ID = 0  # COCO 中 person 的类别 ID


def measure_persons(image: np.ndarray, model) -> tuple[np.ndarray, int]:
    """检测图片中的人员，返回标注后的图像和人数。"""
    results = model(image, classes=[PERSON_CLASS_ID], conf=0.35)
    annotated = image.copy()
    count = 0

    for box in results[0].boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        if cls_id != PERSON_CLASS_ID:
            continue
        count += 1

        # 根据置信度确定边框颜色（绿→蓝绿渐变）
        hue = int(conf * 120)
        color = (0, int(180 + hue * 0.4), int(255 - hue * 0.4))

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        label = f"person {conf:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 8, y1), color, -1)
        cv2.putText(annotated, label, (x1 + 4, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    return annotated, count


# ── 统计展示组件 ────────────────────────────

def show_attendance_stats(expected: int, actual: int):
    """展示四列统计卡片：应到、实到、出勤率、缺勤。"""
    absent = max(0, expected - actual)
    rate = round(actual / expected * 100, 1) if expected > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="stat-card" style="background:linear-gradient(135deg,#1a365d 0%,#2b6cb0 100%);">
            <div class="label">📚 应到人数</div>
            <div class="value">{expected}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card" style="background:linear-gradient(135deg,#22543d 0%,#38a169 100%);">
            <div class="label">✅ 实到人数</div>
            <div class="value present">{actual}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        badge_class = "high" if rate >= 90 else ("medium" if rate >= 70 else "low")
        st.markdown(f"""
        <div class="stat-card" style="background:linear-gradient(135deg,#443018 0%,#d69e2e 100%);">
            <div class="label">📊 出勤率</div>
            <div class="value">{rate}%</div>
            <div style="margin-top:4px;"><span class="rate-badge {badge_class}">{'优秀' if rate>=90 else '良好' if rate>=70 else '偏低'}</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="stat-card" style="background:linear-gradient(135deg,#5a2020 0%,#e53e3e 100%);">
            <div class="label">❌ 缺勤人数</div>
            <div class="value absent">{absent}</div>
        </div>
        """, unsafe_allow_html=True)

    return absent, rate


def show_records_table(records: list[dict]):
    """展示签到记录表格。"""
    if not records:
        st.info("暂无签到记录，上传照片或使用摄像头签到后记录将显示在此处。")
        return

    display = list(reversed(records[-50:]))
    df = pd.DataFrame(display)
    df.columns = ["时间", "班级/课程", "应到", "实到", "缺勤", "出勤率", "备注"]
    df = df.drop(columns=["备注"], errors="ignore")

    def color_rate(val):
        try:
            v = float(str(val).rstrip("%"))
        except (AttributeError, ValueError):
            return ""
        if v >= 90:    return "color: #51cf66; font-weight: 600"
        if v >= 70:    return "color: #ffe066; font-weight: 600"
        return "color: #ff6b6b; font-weight: 600"

    styled = df.style.map(color_rate, subset=["出勤率"])
    st.dataframe(styled, use_container_width=True, hide_index=True,
                 column_config={
                     "时间": st.column_config.Column(width=160),
                     "班级/课程": st.column_config.Column(width=120),
                     "应到": st.column_config.NumberColumn(width=60),
                     "实到": st.column_config.NumberColumn(width=60),
                     "缺勤": st.column_config.NumberColumn(width=60),
                     "出勤率": st.column_config.Column(width=80),
                 })


# ── 侧边栏 ────────────────────────────────

def sidebar():
    """渲染侧边栏，返回 (class_name, expected)。"""
    st.sidebar.markdown("<div class='sidebar-title'>📋 班级签到系统</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sidebar-subtitle'>基于 YOLOv8 智能人数识别</div>", unsafe_allow_html=True)
    st.sidebar.divider()

    class_name = st.sidebar.text_input(
        "📚 班级 / 课程",
        value=st.session_state.get("class_name", "计科2301班"),
        key="sidebar_class"
    )
    expected = st.sidebar.number_input(
        "👥 应到人数",
        min_value=1, max_value=500,
        value=st.session_state.get("expected", 45),
        step=1, key="sidebar_expected"
    )

    st.sidebar.divider()

    records = load_records()
    total = len(records)
    avg_rate = round(sum(r["rate"] for r in records) / total, 1) if total else 0
    st.sidebar.markdown("**📈 历史统计**")
    st.sidebar.markdown(f"- 签到次数：**{total}** 次")
    st.sidebar.markdown(f"- 平均出勤率：**{avg_rate}%**")

    if st.sidebar.button("🗑️ 清空记录", use_container_width=True):
        if st.sidebar.checkbox("确认清空所有签到记录？"):
            save_records([])
            st.rerun()

    st.session_state["class_name"] = class_name
    st.session_state["expected"] = expected
    return class_name, expected


# ── 主程序 ────────────────────────────────

def main():
    class_name, expected = sidebar()

    with st.spinner("正在加载 YOLOv8 模型..."):
        model = load_model()

    tab_photo, tab_camera, tab_records = st.tabs([
        "📷 上传照片签到",
        "🎥 实时监控签到",
        "📋 签到记录",
    ])

    # ── Tab 1: 上传照片 ──────────────────
    with tab_photo:
        st.markdown("##### 上传教室照片，自动识别实到人数")

        file = st.file_uploader("选择照片", type=["jpg", "png", "jpeg"], label_visibility="collapsed")

        if file:
            img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)

            with st.spinner("正在识别人数..."):
                annotated, actual = measure_persons(img, model)

            st.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), use_container_width=True)
            st.divider()

            absent, rate = show_attendance_stats(expected, actual)
            st.divider()

            col_a, col_b = st.columns([1, 3])
            with col_a:
                if st.button("✅ 记录本次签到", type="primary", use_container_width=True):
                    add_record(class_name, expected, actual,
                               note=f"照片签到 (实到{actual}人)")
                    st.success(f"✅ 签到已记录！{class_name} 应到 {expected} 人，实到 {actual} 人，出勤率 {rate}%")
            with col_b:
                st.caption("确认无误后点击「记录本次签到」，数据将保存到签到记录中。")
        else:
            st.info("👆 请上传一张教室照片开始签到")

    # ── Tab 2: 实时监控 ──────────────────
    with tab_camera:
        st.markdown("##### 开启摄像头进行实时人数检测")

        run_cam = st.button("📸 开启摄像头检测", type="primary", use_container_width=True)

        if run_cam:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                st.error("无法连接摄像头，请检查设备权限。")
            else:
                frame_placeholder = st.empty()
                stat_placeholder = st.empty()
                stop_btn = st.button("⏹️ 停止检测")

                while cap.isOpened() and not stop_btn:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    annotated, count = measure_persons(frame, model)

                    frame_placeholder.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB),
                                            channels="RGB", use_container_width=True)

                    with stat_placeholder.container():
                        show_attendance_stats(expected, count)

                cap.release()
                st.info("已停止检测")

    # ── Tab 3: 签到记录 ──────────────────
    with tab_records:
        records = load_records()
        st.markdown(f"##### 签到历史记录 (共 {len(records)} 条)")
        show_records_table(records)

        if records:
            if st.button("📥 导出记录 (CSV)", use_container_width=False):
                df = pd.DataFrame(records)
                csv = df.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    label="下载 CSV",
                    data=csv,
                    file_name=f"attendance_records_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )


if __name__ == "__main__":
    main()
