"""
Облачная версия дашборда для Hugging Face Spaces.
Здесь нет отдельных процессов эмулятора и listener, поэтому всё работает в одном приложении:
каждое обновление страницы = новая секунда показаний датчиков.
"""
import math
import random
import time

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Mine Safety Demo", page_icon="⛏️", layout="wide")

SECTIONS = ["lava-1", "shtrek-2", "uklon-3", "kvershlag-4"]
CH4_WARN, CH4_CRIT = 0.75, 1.0      # учебные пороги — сверить с Правилами промбезопасности
AIR_WARN, AIR_CRIT = 1.0, 0.5

ss = st.session_state
ss.setdefault("t", 0)
ss.setdefault("rows", [])
ss.setdefault("alerts", [])
ss.setdefault("levels", {})
ss.setdefault("incident_start", None)
ss.setdefault("running", True)


def reading(section, t):
    ch4 = 0.25 + 0.05 * math.sin(t / 30) + random.uniform(-0.02, 0.02)
    air = 2.2 + random.uniform(-0.15, 0.15)
    co = 4 + random.uniform(-1, 1)
    if section == "lava-1" and ss.incident_start is not None and t >= ss.incident_start:
        k = t - ss.incident_start
        air = max(0.3, air - 0.04 * k)
        ch4 += 0.02 * k
        co += 0.3 * k if k > 40 else 0
    return {"t": t, "section": section, "ch4_pct": round(ch4, 3),
            "co_ppm": round(co, 1), "air_speed_ms": round(air, 2)}


def evaluate(r):
    level, why = "ok", []
    if r["ch4_pct"] >= CH4_CRIT or r["air_speed_ms"] <= AIR_CRIT:
        level = "critical"
    elif r["ch4_pct"] >= CH4_WARN or r["air_speed_ms"] <= AIR_WARN:
        level = "warning"
    if r["ch4_pct"] >= CH4_WARN:
        why.append(f"CH4 {r['ch4_pct']}%")
    if r["air_speed_ms"] <= AIR_WARN:
        why.append(f"воздух {r['air_speed_ms']} м/с")
    if level != ss.levels.get(r["section"], "ok"):
        ss.levels[r["section"]] = level
        ss.alerts.insert(0, {"сек": r["t"], "участок": r["section"], "уровень": level,
                             "причина": ", ".join(why) or "норма"})


# --- управление ---
st.title("⛏️ Мониторинг безопасности шахты — демо")
c1, c2, c3 = st.columns(3)
if c1.button("🔥 Запустить аварию на lava-1", use_container_width=True):
    ss.incident_start = ss.t
if c2.button("⏯ Пауза / продолжить", use_container_width=True):
    ss.running = not ss.running
if c3.button("↺ Сбросить", use_container_width=True):
    for k in ["t", "rows", "alerts", "levels", "incident_start"]:
        del ss[k]
    st.rerun()

# --- новая «секунда» данных ---
if ss.running:
    for s in SECTIONS:
        r = reading(s, ss.t)
        ss.rows.append(r)
        evaluate(r)
    ss.t += 1
    ss.rows = ss.rows[-600:]

df = pd.DataFrame(ss.rows)
latest = df.groupby("section").tail(1)
cols = st.columns(len(SECTIONS))
for col, (_, r) in zip(cols, latest.iterrows()):
    lvl = ss.levels.get(r["section"], "ok")
    icon = {"ok": "🟢", "warning": "🟡", "critical": "🔴"}[lvl]
    col.metric(f"{icon} {r['section']}", f"CH4 {r['ch4_pct']}%", f"воздух {r['air_speed_ms']} м/с",
               delta_color="off")

left, right = st.columns(2)
left.plotly_chart(px.line(df, x="t", y="ch4_pct", color="section", title="Метан, %"), use_container_width=True)
right.plotly_chart(px.line(df, x="t", y="air_speed_ms", color="section", title="Скорость воздуха, м/с"),
                   use_container_width=True)

st.subheader("Тревоги")
st.dataframe(pd.DataFrame(ss.alerts), use_container_width=True)

if ss.running:
    time.sleep(1)
    st.rerun()
