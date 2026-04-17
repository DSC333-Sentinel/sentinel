
# Sentinel Streamlit Dashboard
# Jose and Aylin
# DSC 333 Final Project · Spring 2026
# Note, to run use:
# streamlit run sentinel_app.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random

# PAGE CONFIGURATION
st.set_page_config(
    page_title="Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# GLOBAL STYLESHEET
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# SIDEBAR NAV
with st.sidebar:
    st.markdown("""
    <div style="padding: 10px 0 24px 0;">
        <div style="font-family:'Space Mono',monospace; font-size:1.3rem; color:#00e5ff; letter-spacing:0.08em;">Sentinel</div>
        <div style="font-size:0.75rem; color:#6b7280; margin-top:4px; font-family:'Space Mono',monospace;">DSC 333 · Spring 2026</div>
    </div>
    """, unsafe_allow_html=True)
 
    page = st.selectbox(
        "Navigate",
        ["Live Feed", "Event History", "Smart Zones", "Settings"],
        label_visibility="collapsed"
    )
 
    st.markdown("---")
 
    # System status (must work on soon)
    st.markdown("**System Status**")
    st.markdown('<span class="badge badge-green">● ONLINE</span>', unsafe_allow_html=True)
    st.caption("Camera · Detected")
    st.caption("Backend · Not connected yet")
    st.caption("GCP Vision · Not configured")
 
    st.markdown("---")
    st.markdown(f"<span style='font-size:0.75rem; color:#6b7280;'>Last updated: {datetime.now().strftime('%H:%M:%S')}</span>", unsafe_allow_html=True)

# LIVE FEED PAGE

if page == "Live Feed":
    st.markdown('<div class="page-header">// LIVE FEED</div>', unsafe_allow_html=True)
 
    col1, col2, col3, col4 = st.columns(4)

    # Sample metrics (to be wired with actual data in future steps)
    col1.metric("Events Today",     "12")
    col2.metric("Unknown Alerts",   "3")
    col3.metric("Active Zones",     "4")
    col4.metric("Persons Detected", "8")
 
    st.markdown("---")
 
    feed_col, info_col = st.columns([3, 1])
 
    with feed_col:
        st.markdown("**Camera Feed**")
        st.markdown("""
        <div style="
            background: #161922;
            border: 1px solid #2a2d3a;
            border-radius: 10px;
            height: 380px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: #6b7280;
            font-family: 'Space Mono', monospace;
            font-size: 0.85rem;
            letter-spacing: 0.05em;
        ">
            <div style="font-size:3rem; margin-bottom:12px;">📷</div>
            <div>CAMERA FEED</div>
            <div style="font-size:0.7rem; margin-top:6px; color:#444;">Connect RPI stream to activate</div>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Stream URL will be wired from the RPI camera module in a future step.")