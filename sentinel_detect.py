"""
Sentinel – Detection Pipeline
==============================
Captures frames from the camera stream, runs GCP Vision object detection,
checks zone overlap, and writes events + snapshots to the database.

Run alongside sentinel.py and sentinel_camera.py:
    python3 sentinel_detect.py
"""

import os
import time
import requests
import cv2
import numpy as np
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv
from google.cloud import vision

load_dotenv()

# CONFIGURATION
CAPTURE_INTERVAL  = int(os.getenv("CAPTURE_INTERVAL", 10))   # seconds between captures
CONFIDENCE_MIN    = float(os.getenv("CONFIDENCE_MIN", 0.55))  # minimum Vision API confidence
SNAPSHOT_DIR      = os.getenv("SNAPSHOT_DIR", "snapshots")

os.makedirs(SNAPSHOT_DIR, exist_ok=True)


# DATABASE
def get_db():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )

def fetch_cameras(conn):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM cameras WHERE active = TRUE ORDER BY id;")
        return cur.fetchall()

def fetch_zones_for_camera(conn, camera_id):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT * FROM zones
            WHERE camera_id = %s OR camera_id IS NULL
            ORDER BY id;
        """, (camera_id,))
        return cur.fetchall()

def insert_event(conn, zone_id, detection_type, alert_level, snapshot_path):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO events (zone_id, detected_at, detection_type, alert_level, snapshot_path)
            VALUES (%s, NOW(), %s, %s, %s);
        """, (zone_id, detection_type, alert_level, snapshot_path))
        conn.commit()

# SNAPSHOT
def save_snapshot(frame_bytes, prefix="snap"):
    filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    path     = os.path.join(SNAPSHOT_DIR, filename)
    with open(path, "wb") as f:
        f.write(frame_bytes)
    return path

# FRAME CAPTURE
def capture_frame(stream_url: str, timeout: int = 5):
    """
    Grabs a single JPEG frame from an MJPEG stream URL.
    Returns raw JPEG bytes or None on failure.
    """
    try:
        resp = requests.get(stream_url, stream=True, timeout=timeout)
        buf  = b""
        for chunk in resp.iter_content(chunk_size=4096):
            buf += chunk
            start = buf.find(b"\xff\xd8")
            end   = buf.find(b"\xff\xd9")
            if start != -1 and end != -1 and end > start:
                return buf[start:end + 2]
    except Exception as e:
        print(f"  [capture] Failed to grab frame from {stream_url}: {e}")
    return None

# GCP VISION DETECTION
def detect_persons(client: vision.ImageAnnotatorClient, image_bytes: bytes) -> list:
    """
    Runs GCP Vision object localisation on image_bytes.
    Returns a list of detected persons above CONFIDENCE_MIN,
    each with their normalized bounding box.
    """
    image   = vision.Image(content=image_bytes)
    response = client.object_localization(image=image)
    persons = []

    for obj in response.localized_object_annotations:
        if obj.name.lower() != "person":
            continue
        if obj.score < CONFIDENCE_MIN:
            continue
        verts = obj.bounding_poly.normalized_vertices
        xs = [v.x for v in verts]
        ys = [v.y for v in verts]
        persons.append({
            "score":  obj.score,
            "x_min": min(xs), "x_max": max(xs),
            "y_min": min(ys), "y_max": max(ys),
            "cx":    (min(xs) + max(xs)) / 2,
            "cy":    (min(ys) + max(ys)) / 2,
        })

    return persons

# ZONE OVERLAP
def find_triggered_zone(persons: list, zones: list):
    """
    Returns the highest-alert zone that contains at least one detected person,
    or None if no overlap found.
    """
    priority = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    best_zone = None
    best_prio = 0

    for zone in zones:
        for person in persons:
            # Check if person center falls inside zone bounding box
            if (zone["x1"] <= person["cx"] <= zone["x2"] and
                    zone["y1"] <= person["cy"] <= zone["y2"]):
                p = priority.get(zone["alert_level"], 0)
                if p > best_prio:
                    best_prio = p
                    best_zone = zone

    return best_zone

# MAIN LOOP
def main():
    print("\n[sentinel_detect] Starting detection pipeline...")

    # Validate GCP credentials
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not creds_path or not os.path.exists(creds_path):
        raise EnvironmentError(
            "GOOGLE_APPLICATION_CREDENTIALS not set or file not found. "
            "Check your .env file."
        )

    vision_client = vision.ImageAnnotatorClient()
    print("[sentinel_detect] GCP Vision client initialised.")

    conn = get_db()
    print("[sentinel_detect] Database connected.")
    print(f"[sentinel_detect] Capturing every {CAPTURE_INTERVAL}s. Press Ctrl+C to stop.\n")

    try:
        while True:
            cameras = fetch_cameras(conn)
            if not cameras:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No active cameras found. Waiting...")
                time.sleep(CAPTURE_INTERVAL)
                continue

            for cam in cameras:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] Checking camera: {cam['name']} ({cam['stream_url']})")

                # Capture frame
                frame_bytes = capture_frame(cam["stream_url"])
                if frame_bytes is None:
                    print(f"  [skip] Could not capture frame from {cam['name']}")
                    continue

                # Run Vision API
                persons = detect_persons(vision_client, frame_bytes)
                print(f"  Persons detected: {len(persons)}")

                if persons:
                    # Check zone overlap
                    zones = fetch_zones_for_camera(conn, cam["id"])
                    triggered_zone = find_triggered_zone(persons, zones)

                    snapshot_path = save_snapshot(
                        frame_bytes,
                        prefix=f"cam{cam['id']}"
                    )

                    if triggered_zone:
                        alert = triggered_zone["alert_level"]
                        print(f"  ⚠ Zone triggered: '{triggered_zone['name']}' [{alert}]")
                        insert_event(conn, triggered_zone["id"], "Person Detected", alert, snapshot_path)
                    else:
                        # Person detected but not in any defined zone — log as LOW
                        print(f"  Person detected outside all zones — logging as LOW")
                        insert_event(conn, None, "Person Detected", "LOW", snapshot_path)
                else:
                    # No person — log motion only if you want a full activity log
                    # Uncomment the line below to log every capture, or leave it
                    # to only log when a person is detected.
                    # insert_event(conn, None, "Motion Only", "LOW", None)
                    print(f"  No persons detected.")

            time.sleep(CAPTURE_INTERVAL)

    except KeyboardInterrupt:
        print("\n[sentinel_detect] Stopped by user.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()