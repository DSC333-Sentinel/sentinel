
"""
Sentinel Streamlit Dashboard
Jose and Aylin
DSC 333 Final Project · Spring 2026
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
    """Creates the zones and events tables if they don't exist yet."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS zones (
                id          SERIAL PRIMARY KEY,
                name        TEXT NOT NULL,
                alert_level TEXT NOT NULL CHECK (alert_level IN ('HIGH','MEDIUM','LOW')),
                x1          REAL NOT NULL,
                y1          REAL NOT NULL,
                x2          REAL NOT NULL,
                y2          REAL NOT NULL,
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
 
def fetch_zones(conn):
    with get_cursor(conn) as cur:
        cur.execute("""
            SELECT z.id, z.name, z.alert_level, z.x1, z.y1, z.x2, z.y2,
                   COUNT(e.id) AS event_count
            FROM zones z
            LEFT JOIN events e ON e.zone_id = z.id
            GROUP BY z.id ORDER BY z.id;
        """)
        return cur.fetchall()
 
def insert_zone(conn, name, alert_level, x1, y1, x2, y2):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO zones (name, alert_level, x1, y1, x2, y2)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (name, alert_level, x1, y1, x2, y2))
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
    st.caption("Camera · Not connected yet")
    st.caption("GCP Vision · Not configured")
 
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
                    st.image(cam["stream_url"], use_container_width=True)
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
        📌 Zones define regions in the camera frame. Coordinates are <b>normalized (0.0–1.0)</b>
        relative to frame width/height. Each zone has its own alert level.
    </div>
    """, unsafe_allow_html=True)
 
    zones_col, form_col = st.columns([1.4, 1])
 
    with zones_col:
        st.markdown("**Configured Zones**")
        zones = fetch_zones(conn)
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
            st.caption("No zones yet. Add one using the form.")
 
    with form_col:
        st.markdown("**Add New Zone**")
        with st.form("add_zone_form", clear_on_submit=True):
            zone_name = st.text_input("Zone Name", placeholder="e.g. Front Door")
            alert_lvl = st.selectbox("Alert Level", ["HIGH", "MEDIUM", "LOW"])
            st.markdown("**Bounding Box** *(0.0 – 1.0)*")
            c1, c2 = st.columns(2)
            x1 = c1.number_input("X1 (left)",   0.0, 1.0, 0.0, 0.01)
            y1 = c2.number_input("Y1 (top)",    0.0, 1.0, 0.0, 0.01)
            x2 = c1.number_input("X2 (right)",  0.0, 1.0, 0.5, 0.01)
            y2 = c2.number_input("Y2 (bottom)", 0.0, 1.0, 0.5, 0.01)
            if st.form_submit_button("➕ Add Zone"):
                if not zone_name.strip():
                    st.error("Zone name cannot be empty.")
                elif x2 <= x1 or y2 <= y1:
                    st.error("X2 must be > X1 and Y2 must be > Y1.")
                else:
                    insert_zone(conn, zone_name.strip(), alert_lvl, x1, y1, x2, y2)
                    st.success(f"Zone '{zone_name}' added!")
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
                st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                if st.button(f"🗑 Delete '{cam['name']}'", key=f"delcam_{cam['id']}"):
                    delete_camera(conn, cam["id"])
                    st.success(f"Camera '{cam['name']}' removed.")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
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
    if st.button("🗑 Clear All Events"):
        with conn.cursor() as cur:
            cur.execute("DELETE FROM events;")
            conn.commit()
        st.success("All events cleared.")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)