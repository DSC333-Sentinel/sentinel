
"""
Sentinel Streamlit Dashboard
Jose and Aylin
DSC 333 Final Project · Spring 2026
==============================

Note, to run use:
streamlit run sentinel.py
"""

import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random
import cv2
 
load_dotenv()

SNAPSHOT_DIR = os.getenv("SNAPSHOT_DIR", "snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

# PAGE CONFIGURATION
st.set_page_config(
    page_title="Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# GLOBAL STYLESHEET
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
 
:root {
    --bg:      #0d0f14;
    --surface: #161922;
    --border:  #2a2d3a;
    --accent:  #00e5ff;
    --accent2: #ff4d6d;
    --green:   #00e676;
    --yellow:  #ffd600;
    --text:    #e8eaf0;
    --muted:   #6b7280;
    --mono:    'Space Mono', monospace;
    --sans:    'DM Sans', sans-serif;
}
html, body, [class*="css"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--sans) !important;
}
section[data-testid="stSidebar"] {
    background-color: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 20px;
}
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 0.78rem !important; letter-spacing: 0.08em; text-transform: uppercase; }
[data-testid="stMetricValue"] { color: var(--accent) !important; font-family: var(--mono) !important; font-size: 2rem !important; }
.stButton > button {
    background: transparent !important;
    border: 1px solid var(--accent) !important;
    color: var(--accent) !important;
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
    border-radius: 6px !important;
    transition: all 0.2s ease;
}
.stButton > button:hover { background: var(--accent) !important; color: #000 !important; }
.danger-btn > button { border-color: var(--accent2) !important; color: var(--accent2) !important; }
.danger-btn > button:hover { background: var(--accent2) !important; color: #fff !important; }
.stTextInput input, .stSelectbox select, .stNumberInput input {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 6px !important;
}
[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
hr { border-color: var(--border) !important; margin: 1.5rem 0; }
.page-header {
    font-family: var(--mono);
    font-size: 1.4rem;
    color: var(--accent);
    letter-spacing: 0.06em;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.6rem;
    margin-bottom: 1.5rem;
}
.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-family: var(--mono); font-weight: 700; letter-spacing: 0.05em; }
.badge-green  { background: #00e67622; color: #00e676; border: 1px solid #00e67655; }
.badge-red    { background: #ff4d6d22; color: #ff4d6d; border: 1px solid #ff4d6d55; }
.badge-yellow { background: #ffd60022; color: #ffd600; border: 1px solid #ffd60055; }
.badge-blue   { background: #00e5ff22; color: #00e5ff; border: 1px solid #00e5ff55; }
.zone-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px 20px; margin-bottom: 12px;
}
.zone-card h4 { margin: 0 0 4px 0; font-family: var(--mono); color: var(--accent); font-size: 0.95rem; }
.zone-card p  { margin: 0; font-size: 0.82rem; color: var(--muted); }
.info-box {
    background: #00e5ff0d; border: 1px solid #00e5ff33;
    border-radius: 8px; padding: 14px 18px;
    font-size: 0.88rem; color: var(--text); margin-bottom: 16px;
}
.error-box {
    background: #ff4d6d0d; border: 1px solid #ff4d6d44;
    border-radius: 8px; padding: 14px 18px;
    font-size: 0.88rem; color: var(--text); margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)
 
# DATABASE CONNECTION
@st.cache_resource
def get_connection():
    """
    Opens a persistent psycopg2 connection using credentials
    from a .env file. Cached across reruns.
    """
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )
 
def get_cursor(conn):
    """Returns a RealDictCursor for dict-style row access."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# SCHEMA INIT
def init_db(conn):
    """Creates all tables if they don't exist yet."""
    with conn.cursor() as cur:
        # cameras must be created first — zones references it
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cameras (
                id         SERIAL PRIMARY KEY,
                name       TEXT NOT NULL,
                stream_url TEXT NOT NULL,
                location   TEXT,
                active     BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS zones (
                id          SERIAL PRIMARY KEY,
                name        TEXT NOT NULL,
                alert_level TEXT NOT NULL CHECK (alert_level IN ('HIGH','MEDIUM','LOW')),
                x1          REAL NOT NULL,
                y1          REAL NOT NULL,
                x2          REAL NOT NULL,
                y2          REAL NOT NULL,
                camera_id   INTEGER REFERENCES cameras(id) ON DELETE SET NULL,
                created_at  TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id             SERIAL PRIMARY KEY,
                zone_id        INTEGER REFERENCES zones(id) ON DELETE SET NULL,
                detected_at    TIMESTAMP NOT NULL DEFAULT NOW(),
                detection_type TEXT NOT NULL CHECK (detection_type IN ('Person Detected','Motion Only')),
                alert_level    TEXT NOT NULL CHECK (alert_level IN ('HIGH','MEDIUM','LOW')),
                snapshot_path  TEXT
            );
        """)
        # Migration safety net — adds camera_id to zones if it was created
        # before this schema change (e.g. your own existing database)
        cur.execute("""
            ALTER TABLE zones ADD COLUMN IF NOT EXISTS
            camera_id INTEGER REFERENCES cameras(id) ON DELETE SET NULL;
        """)
        conn.commit()

# SEED DATA
def seed_data(conn):
    """
    Populates the DB with sample zones and events for testing.
    Returns False (and does nothing) if the zones table already has rows.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM zones;")
        if cur.fetchone()[0] > 0:
            return False
 
        sample_zones = [
            ("Front Door", "HIGH",   0.0, 0.0, 0.4, 0.5),
            ("Backyard",   "MEDIUM", 0.4, 0.0, 1.0, 0.6),
            ("Garage",     "LOW",    0.0, 0.5, 0.5, 1.0),
            ("Side Gate",  "HIGH",   0.5, 0.5, 1.0, 1.0),
        ]
        zone_ids = []
        for z in sample_zones:
            cur.execute("""
                INSERT INTO zones (name, alert_level, x1, y1, x2, y2)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
            """, z)
            zone_ids.append(cur.fetchone()[0])
 
        detection_types = ["Person Detected", "Motion Only"]
        alert_levels    = ["HIGH", "HIGH", "MEDIUM", "LOW", "LOW"]
        for _ in range(40):
            ts = datetime.now() - timedelta(minutes=random.randint(1, 60 * 72))
            cur.execute("""
                INSERT INTO events (zone_id, detected_at, detection_type, alert_level)
                VALUES (%s, %s, %s, %s);
            """, (
                random.choice(zone_ids),
                ts,
                random.choice(detection_types),
                random.choice(alert_levels),
            ))
 
        conn.commit()
        return True

# QUERY HELPERS
def fetch_events(conn, zone_id=None, detection_type=None, alert_level=None, limit=200):
    with get_cursor(conn) as cur:
        sql = """
            SELECT e.id, e.detected_at, z.name AS zone,
                   e.detection_type, e.alert_level, e.snapshot_path
            FROM events e
            LEFT JOIN zones z ON e.zone_id = z.id
            WHERE 1=1
        """
        params = []
        if zone_id:
            sql += " AND e.zone_id = %s";        params.append(zone_id)
        if detection_type:
            sql += " AND e.detection_type = %s"; params.append(detection_type)
        if alert_level:
            sql += " AND e.alert_level = %s";    params.append(alert_level)
        sql += " ORDER BY e.detected_at DESC LIMIT %s"; params.append(limit)
        cur.execute(sql, params)
        return cur.fetchall()
 
def fetch_zones(conn, camera_id=None):
    with get_cursor(conn) as cur:
        sql = """
            SELECT z.id, z.name, z.alert_level, z.x1, z.y1, z.x2, z.y2,
                   z.camera_id, c.name AS camera_name,
                   COUNT(e.id) AS event_count
            FROM zones z
            LEFT JOIN events e ON e.zone_id = z.id
            LEFT JOIN cameras c ON z.camera_id = c.id
            WHERE 1=1
        """
        params = []
        if camera_id:
            sql += " AND z.camera_id = %s"; params.append(camera_id)
        sql += " GROUP BY z.id, c.name ORDER BY z.id"
        cur.execute(sql, params)
        return cur.fetchall()
 
def insert_zone(conn, name, alert_level, x1, y1, x2, y2, camera_id=None):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO zones (name, alert_level, x1, y1, x2, y2, camera_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (name, alert_level, x1, y1, x2, y2, camera_id))
        conn.commit()
 
def delete_zone(conn, zone_id):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM zones WHERE id = %s;", (zone_id,))
        conn.commit()
 
def fetch_summary(conn):
    today = datetime.now().date()
    with get_cursor(conn) as cur:
        cur.execute("SELECT COUNT(*) AS c FROM events WHERE detected_at::date = %s;", (today,))
        events_today = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM events WHERE alert_level='HIGH' AND detected_at::date = %s;", (today,))
        high_alerts = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM zones;")
        zone_count = cur.fetchone()["c"]
    return events_today, high_alerts, zone_count

def fetch_cameras(conn):
    with get_cursor(conn) as cur:
        cur.execute("SELECT * FROM cameras WHERE active = TRUE ORDER BY id;")
        return cur.fetchall()

def insert_camera(conn, name, stream_url, location):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO cameras (name, stream_url, location)
            VALUES (%s, %s, %s);
        """, (name, stream_url, location))
        conn.commit()

def delete_camera(conn, camera_id):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM cameras WHERE id = %s;", (camera_id,))
        conn.commit()

def update_camera(conn, camera_id, name, stream_url, location):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE cameras SET name=%s, stream_url=%s, location=%s
            WHERE id=%s;
        """, (name, stream_url, location, camera_id))
        conn.commit()

# CONNECT & INIT
db_ok    = False
conn     = None
db_error = ""
 
try:
    conn = get_connection()
    init_db(conn)
    db_ok = True
except Exception as e:
    db_error = str(e)
 
ALERT_BADGE = {
    "HIGH":   '<span class="badge badge-red">HIGH</span>',
    "MEDIUM": '<span class="badge badge-yellow">MEDIUM</span>',
    "LOW":    '<span class="badge badge-green">LOW</span>',
}

# SIDEBAR
with st.sidebar:
    st.markdown("""
    <div style="padding:10px 0 24px 0;">
        <div style="font-family:'Space Mono',monospace;font-size:1.3rem;color:#00e5ff;letter-spacing:0.08em;">Sentinel</div>
        <div style="font-size:0.75rem;color:#6b7280;margin-top:4px;font-family:'Space Mono',monospace;">DSC 333 · Spring 2026</div>
    </div>
    """, unsafe_allow_html=True)
 
    page = st.selectbox(
        "Navigate",
        ["Live Feed", "Event History", "Smart Zones", "Cameras", "Settings"],
        label_visibility="collapsed",
    )
 
    st.markdown("---")
    st.markdown("**System Status**")
    if db_ok:
        st.markdown('<span class="badge badge-green">● DB CONNECTED</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge badge-red">● DB OFFLINE</span>', unsafe_allow_html=True)
    # Camera status — check if any active cameras exist in DB
    if db_ok:
        cams = fetch_cameras(conn)
        if cams:
            st.markdown(f'<span class="badge badge-green">● {len(cams)} Camera(s) Active</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge badge-red">● No Cameras Added</span>', unsafe_allow_html=True)
    else:
        st.caption("Camera · DB offline")

    # GCP Vision status — check credentials file exists
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds_path and os.path.exists(creds_path):
        st.markdown('<span class="badge badge-green">● GCP Vision Ready</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge badge-red">● GCP Vision Not Configured</span>', unsafe_allow_html=True)
 
    st.markdown("---")
    if db_ok:
        if st.button("Seed Sample Data"):
            seeded = seed_data(conn)
            if seeded:
                st.success("Sample data seeded!")
                st.rerun()
            else:
                st.info("DB already has data.")
 
    st.markdown(f"<span style='font-size:0.75rem;color:#6b7280;'>Updated: {datetime.now().strftime('%H:%M:%S')}</span>", unsafe_allow_html=True)

# DB OFFLINE GUARD
if not db_ok:
    st.markdown(f"""
    <div class="error-box">
        ⚠️ <b>Could not connect to PostgreSQL.</b><br>
        Check your <code>.env</code> file and make sure the database server is running.<br>
        <span style="color:#6b7280;font-size:0.82rem;">{db_error}</span>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# PAGE: LIVE FEED
if page == "Live Feed":
    st.markdown('<div class="page-header">// LIVE FEED</div>', unsafe_allow_html=True)
 
    events_today, high_alerts, zone_count = fetch_summary(conn)
    c1, c2, c3 = st.columns(3)
    c1.metric("Events Today", events_today)
    c2.metric("High Alerts",  high_alerts)
    c3.metric("Active Zones", zone_count)
 
    st.markdown("---")
    feed_col, info_col = st.columns([3, 1])
 
    with feed_col:
        st.markdown("**Camera Feed**")
        cameras = fetch_cameras(conn)
        if cameras:
            grid = st.columns(2)
            for i, cam in enumerate(cameras):
                with grid[i % 2]:
                    location_label = f" — {cam['location']}" if cam["location"] else ""
                    st.markdown(f"<span style='font-family:var(--mono);color:var(--accent);font-size:0.82rem;'>{cam['name']}{location_label}</span>", unsafe_allow_html=True)
                    st.image(cam["stream_url"], width='stretch')
        else:
            st.markdown("""
            <div style="background:#161922;border:1px solid #2a2d3a;border-radius:10px;
                        height:380px;display:flex;flex-direction:column;
                        align-items:center;justify-content:center;
                        color:#6b7280;font-family:'Space Mono',monospace;
                        font-size:0.85rem;letter-spacing:0.05em;">
                <div style="font-size:3rem;margin-bottom:12px;">📷</div>
                <div>CAMERA FEED</div>
                <div style="font-size:0.7rem;margin-top:6px;color:#444;">No cameras configured yet</div>
            </div>
            """, unsafe_allow_html=True)
            st.caption("Go to the Cameras page to add a stream.")
 
    with info_col:
        st.markdown("**Recent Events**")
        recent = fetch_events(conn, limit=6)
        if recent:
            for row in recent:
                color = "#ff4d6d" if row["alert_level"] == "HIGH" else (
                        "#ffd600" if row["alert_level"] == "MEDIUM" else "#00e676")
                ts_str     = row["detected_at"].strftime("%H:%M:%S") if row["detected_at"] else "—"
                zone_label = row["zone"] or "Unknown Zone"
                st.markdown(f"""
                <div style="border-left:3px solid {color};padding:8px 12px;margin-bottom:8px;
                            background:#161922;border-radius:0 6px 6px 0;font-size:0.8rem;">
                    <div style="color:{color};font-family:'Space Mono',monospace;font-size:0.7rem;">{row['alert_level']}</div>
                    <div style="color:#e8eaf0;">{row['detection_type']}</div>
                    <div style="color:#6b7280;font-size:0.72rem;">{zone_label}</div>
                    <div style="color:#444;font-size:0.68rem;">{ts_str}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No events yet. Use the Seed Sample Data in the sidebar.")

# PAGE: EVENT HISTORY
elif page == "Event History":
    st.markdown('<div class="page-header">// EVENT HISTORY</div>', unsafe_allow_html=True)
 
    zones = fetch_zones(conn)
    zone_options = {"All Zones": None} | {z["name"]: z["id"] for z in zones}
 
    f1, f2, f3 = st.columns(3)
    with f1:
        zone_sel  = st.selectbox("Filter by Zone",  list(zone_options.keys()))
    with f2:
        type_sel  = st.selectbox("Filter by Type",  ["All Types", "Person Detected", "Motion Only"])
    with f3:
        alert_sel = st.selectbox("Filter by Alert", ["All Levels", "HIGH", "MEDIUM", "LOW"])
 
    events = fetch_events(
        conn,
        zone_id        = zone_options[zone_sel],
        detection_type = None if type_sel  == "All Types"  else type_sel,
        alert_level    = None if alert_sel == "All Levels" else alert_sel,
    )
 
    st.markdown("---")
    st.caption(f"Showing {len(events)} events")
 
    if events:
        df = pd.DataFrame([dict(r) for r in events])
        df["detected_at"] = df["detected_at"].astype(str)
        df = df.rename(columns={
            "id": "ID", "detected_at": "Timestamp", "zone": "Zone",
            "detection_type": "Type", "alert_level": "Alert", "snapshot_path": "Snapshot",
        })
        df["Snapshot"] = df["Snapshot"].fillna("—")
        st.dataframe(df[["ID", "Timestamp", "Zone", "Type", "Alert", "Snapshot"]], width="stretch", hide_index=True)
        st.markdown("---")
        st.download_button("⬇ Download CSV", data=df.to_csv(index=False),
                           file_name="sentinel_events.csv", mime="text/csv")
    else:
        st.info("No events match the selected filters.")

# PAGE: SMART ZONES
elif page == "Smart Zones":
    st.markdown('<div class="page-header">// SMART ZONES</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
        📌 Zones define regions in the camera frame. Select a camera to preview its stream
        and configure zones for it. Coordinates are <b>normalized (0.0–1.0)</b> relative to frame width/height.
    </div>
    """, unsafe_allow_html=True)

    # Camera selector
    cameras = fetch_cameras(conn)
    if not cameras:
        st.warning("No cameras configured yet. Go to the Cameras page to add one first.")
    else:
        cam_options = {c["name"]: c["id"] for c in cameras}
        selected_cam_name = st.selectbox("Select Camera", list(cam_options.keys()))
        selected_cam_id   = cam_options[selected_cam_name]
        selected_cam_url  = next(c["stream_url"] for c in cameras if c["id"] == selected_cam_id)

        st.markdown("---")
        zones_col, form_col = st.columns([1.4, 1])

        with zones_col:
            # Camera preview
            st.markdown(f"**Preview — {selected_cam_name}**")
            try:
                st.image(selected_cam_url, use_container_width=True)
            except Exception:
                st.markdown("""
                <div style="background:#161922;border:1px solid #2a2d3a;border-radius:10px;
                            height:200px;display:flex;align-items:center;justify-content:center;
                            color:#6b7280;font-family:'Space Mono',monospace;font-size:0.8rem;">
                    Stream unavailable
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"**Zones for {selected_cam_name}**")
            zones = fetch_zones(conn, camera_id=selected_cam_id)
            if zones:
                for z in zones:
                    badge  = ALERT_BADGE.get(z["alert_level"], "")
                    coords = f"({z['x1']:.2f}, {z['y1']:.2f}) → ({z['x2']:.2f}, {z['y2']:.2f})"
                    st.markdown(f"""
                    <div class="zone-card">
                        <h4>{z['name']}</h4>
                        <p>Coordinates: <code style="color:#00e5ff">{coords}</code></p>
                        <p style="margin-top:6px;">Alert Level: {badge} &nbsp;·&nbsp; Events: <b style="color:#e8eaf0">{z['event_count']}</b></p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                    if st.button(f"🗑 Delete '{z['name']}'", key=f"del_{z['id']}"):
                        delete_zone(conn, z["id"])
                        st.success(f"Zone '{z['name']}' deleted.")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.caption(f"No zones for {selected_cam_name} yet. Add one using the form.")

        with form_col:
            st.markdown("**Add New Zone**")

            zone_name = st.text_input("Zone Name", placeholder="e.g. Front Door")
            alert_lvl = st.selectbox("Alert Level", ["HIGH", "MEDIUM", "LOW"])

            st.markdown("**Bounding Box** *(0.0 – 1.0)*")
            x1 = st.slider("X1 (left)",   0.0, 1.0, 0.0, 0.01, key="zx1")
            y1 = st.slider("Y1 (top)",    0.0, 1.0, 0.0, 0.01, key="zy1")
            x2 = st.slider("X2 (right)",  0.0, 1.0, 0.5, 0.01, key="zx2")
            y2 = st.slider("Y2 (bottom)", 0.0, 1.0, 0.5, 0.01, key="zy2")

            # ── Zone Preview ──────────────────────────────
            st.markdown("**Zone Preview**")

            cap_col, _ = st.columns([1, 1])
            with cap_col:
                if st.button("📸 Capture Frame", key="capture_preview"):
                    frame_bytes = None
                    try:
                        import requests as req
                        resp = req.get(selected_cam_url, stream=True, timeout=5)
                        buf  = b""
                        for chunk in resp.iter_content(chunk_size=4096):
                            buf += chunk
                            s = buf.find(b"\xff\xd8")
                            e = buf.find(b"\xff\xd9")
                            if s != -1 and e != -1 and e > s:
                                frame_bytes = buf[s:e + 2]
                                break
                    except Exception:
                        pass
                    if frame_bytes:
                        st.session_state["preview_frame"] = frame_bytes
                    else:
                        st.error("Could not grab frame. Is the stream running?")

            if "preview_frame" in st.session_state:
                import numpy as np
                frame_arr = np.frombuffer(st.session_state["preview_frame"], np.uint8)
                frame_bgr = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)

                if frame_bgr is not None:
                    h, w = frame_bgr.shape[:2]

                    # Draw all existing zones for this camera in grey
                    existing_zones = fetch_zones(conn, camera_id=selected_cam_id)
                    for z in existing_zones:
                        px1 = int(z["x1"] * w); py1 = int(z["y1"] * h)
                        px2 = int(z["x2"] * w); py2 = int(z["y2"] * h)
                        cv2.rectangle(frame_bgr, (px1, py1), (px2, py2), (100, 100, 100), 1)
                        cv2.putText(frame_bgr, z["name"], (px1 + 4, py1 + 14),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)

                    # Draw the new zone being configured in cyan
                    if x2 > x1 and y2 > y1:
                        nx1 = int(x1 * w); ny1 = int(y1 * h)
                        nx2 = int(x2 * w); ny2 = int(y2 * h)
                        cv2.rectangle(frame_bgr, (nx1, ny1), (nx2, ny2), (0, 229, 255), 2)
                        label = zone_name.strip() if zone_name.strip() else "New Zone"
                        cv2.putText(frame_bgr, label, (nx1 + 4, ny1 + 16),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 229, 255), 1)

                    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                    st.image(frame_rgb, use_container_width=True)
            else:
                st.markdown("""
                <div style="background:#161922;border:1px solid #2a2d3a;border-radius:8px;
                            height:140px;display:flex;align-items:center;justify-content:center;
                            color:#6b7280;font-family:'Space Mono',monospace;font-size:0.75rem;">
                    Press 📸 Capture Frame to preview
                </div>
                """, unsafe_allow_html=True)

            # ── Submit ────────────────────────────────────
            st.markdown("")
            if st.button("➕ Add Zone", key="add_zone_btn", use_container_width=True):
                if not zone_name.strip():
                    st.error("Zone name cannot be empty.")
                elif x2 <= x1 or y2 <= y1:
                    st.error("X2 must be > X1 and Y2 must be > Y1.")
                else:
                    insert_zone(conn, zone_name.strip(), alert_lvl, x1, y1, x2, y2, selected_cam_id)
                    st.session_state.pop("preview_frame", None)
                    st.success(f"Zone '{zone_name}' added to {selected_cam_name}!")
                    st.rerun()

# PAGE: CAMERAS
elif page == "Cameras":
    st.markdown('<div class="page-header">// CAMERAS</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
        Add camera streams here. Each stream URL should point to a running
        <code>sentinel_camera.py</code> instance. They will appear as a grid on the Live Feed page.
    </div>
    """, unsafe_allow_html=True)

    cameras_col, form_col = st.columns([1.4, 1])

    with cameras_col:
        st.markdown("**Registered Cameras**")
        cameras = fetch_cameras(conn)
        if cameras:
            for cam in cameras:
                location_label = cam["location"] or "No location set"
                st.markdown(f"""
                <div class="zone-card">
                    <h4>{cam['name']}</h4>
                    <p>Location: <b style="color:#e8eaf0">{location_label}</b></p>
                    <p style="margin-top:4px;">URL: <code style="color:#00e5ff">{cam['stream_url']}</code></p>
                </div>
                """, unsafe_allow_html=True)

                edit_col, del_col = st.columns([1, 1])
                with edit_col:
                    if st.button(f"✏️ Edit '{cam['name']}'", key=f"editcam_{cam['id']}"):
                        st.session_state[f"editing_cam"] = cam["id"]
                with del_col:
                    st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                    if st.button(f"🗑 Delete", key=f"delcam_{cam['id']}"):
                        delete_camera(conn, cam["id"])
                        st.success(f"Camera '{cam['name']}' removed.")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                # Inline edit form
                if st.session_state.get("editing_cam") == cam["id"]:
                    with st.form(f"edit_cam_form_{cam['id']}", clear_on_submit=True):
                        st.markdown("**Edit Camera**")
                        new_name     = st.text_input("Camera Name", value=cam["name"])
                        new_url      = st.text_input("Stream URL",  value=cam["stream_url"])
                        new_location = st.text_input("Location",    value=cam["location"] or "")
                        s1, s2 = st.columns(2)
                        if s1.form_submit_button("💾 Save"):
                            if not new_name.strip() or not new_url.strip():
                                st.error("Name and URL cannot be empty.")
                            else:
                                update_camera(conn, cam["id"], new_name.strip(), new_url.strip(), new_location.strip() or None)
                                st.session_state.pop("editing_cam", None)
                                st.success("Camera updated!")
                                st.rerun()
                        if s2.form_submit_button("✖ Cancel"):
                            st.session_state.pop("editing_cam", None)
                            st.rerun()
        else:
            st.caption("No cameras yet. Add one using the form.")

    with form_col:
        st.markdown("**Add New Camera**")
        with st.form("add_camera_form", clear_on_submit=True):
            cam_name     = st.text_input("Camera Name",   placeholder="e.g. Front Door Cam")
            cam_url      = st.text_input("Stream URL",    placeholder="http://192.168.1.10:8080/stream")
            cam_location = st.text_input("Location",      placeholder="e.g. Front Porch")
            if st.form_submit_button("➕ Add Camera"):
                if not cam_name.strip():
                    st.error("Camera name cannot be empty.")
                elif not cam_url.strip():
                    st.error("Stream URL cannot be empty.")
                else:
                    insert_camera(conn, cam_name.strip(), cam_url.strip(), cam_location.strip() or None)
                    st.success(f"Camera '{cam_name}' added!")
                    st.rerun()

# PAGE: SETTINGS
elif page == "Settings":
    st.markdown('<div class="page-header">// SETTINGS</div>', unsafe_allow_html=True)
 
    st.markdown("**Database**")
    st.markdown("""
    <div class="info-box">
        Connection is configured via your <code>.env</code> file.
        Tables are created automatically on first launch.
    </div>
    """, unsafe_allow_html=True)
    try:
        with get_cursor(conn) as cur:
            cur.execute("SELECT COUNT(*) AS c FROM zones;");  zc = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM events;"); ec = cur.fetchone()["c"]
        st.markdown(f'<span class="badge badge-green">● Connected</span> &nbsp; zones: <b>{zc}</b> &nbsp;·&nbsp; events: <b>{ec}</b>', unsafe_allow_html=True)
    except Exception as ex:
        st.markdown(f'<span class="badge badge-red">● Error: {ex}</span>', unsafe_allow_html=True)
 
    st.markdown("---")
    st.markdown("**Camera**")
    st.markdown("""
    <div class="info-box">
        Camera streams are managed on the <b>Cameras</b> page.
    </div>
    """, unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.number_input("Capture Interval (seconds)", 1, 60, 5)
    c2.number_input("Motion Sensitivity (0–100)", 0, 100, 50)
 
    st.markdown("---")
    st.markdown("**GCP Configuration**")
    c1, c2 = st.columns(2)
    c1.text_input("GCP Project ID", placeholder="my-gcp-project")
    c2.selectbox("Vision API Model", ["builtin/stable", "builtin/latest"])
 
    st.markdown("---")
    st.markdown("**Danger Zone**")
    st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
    if st.button("Clear All Events"):
        with conn.cursor() as cur:
            cur.execute("DELETE FROM events;")
            conn.commit()
        st.success("All events cleared.")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)