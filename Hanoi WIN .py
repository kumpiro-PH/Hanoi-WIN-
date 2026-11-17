import os
from collections import Counter, defaultdict
import pandas as pd
import streamlit as st

# ================================================================
# HANOI AI PROFESSIONAL v2.0 (Streamlit Web App Edition)
# ================================================================

st.set_page_config(
    page_title="HANOI AI PROFESSIONAL v2.0",
    page_icon="🎯",
    layout="wide",
)

CSV_FILE = "history_hanoi.csv"
MIN_HISTORY_FOR_DYNAMIC_WEIGHT = 10
RECENT_WINDOW = 30

# ชุดเลขประจำวันตั้งต้น (คุณสามารถแก้ไขตัวเลขในนี้ได้ตามต้องการ)
DEFAULT_DAILY_NUMBERS = {
    "Monday": "194286",
    "Tuesday": "194286",
    "Wednesday": "431560",
    "Thursday": "541609",
    "Friday": "865032",
    "Saturday": "319820",
    "Sunday": "325984",
}

FORMULAS = [
    "Carry Over",
    "±1",
    "Sum Modulo",
    "Cross Sum",
    "Daily 6-Digit",
    "Rotation",
    "Mirror",
    "Shift +2",
    "Double",
    "Sandwich",
]


def zfill_num(value, width):
    try:
        if pd.isna(value):
            return "0" * width
        s = str(value).strip()
        if "." in s:
            s = s.split(".")[0]
        return s.zfill(width)[-width:]
    except Exception:
        return "0" * width


def parse_thai_date(x):
    """แปลง DD/MM/YYYY พ.ศ. เป็น Timestamp ค.ศ. แบบปลอดภัย"""
    try:
        parts = str(x).strip().split("/")
        if len(parts) != 3:
            return pd.NaT
        day, month, year = map(int, parts)
        if year < 100:
            year += 2500
        if year >= 2400:
            year -= 543
        return pd.Timestamp(year=year, month=month, day=day)
    except Exception:
        return pd.NaT


def initialize_csv():
    if not os.path.exists(CSV_FILE):
        initial_data = [
            ["30/09/2569", "95242", "82585", "242", "85"],
            ["29/09/2569", "05651", "08389", "651", "89"],
            ["28/09/2569", "77115", "86908", "115", "08"],
        ]
        pd.DataFrame(
            initial_data,
            columns=["date", "special", "first_prize", "top_3", "bottom_2"],
        ).to_csv(CSV_FILE, index=False, encoding="utf-8-sig")


def load_history():
    if not os.path.exists(CSV_FILE):
        initialize_csv()
    df = pd.read_csv(CSV_FILE, dtype=str).fillna("")
    required = ["date", "special", "first_prize", "top_3", "bottom_2"]
    for col in required:
        if col not in df.columns:
            df[col] = ""
    df["dt"] = df["date"].apply(parse_thai_date)
    df = df.dropna(subset=["dt"]).copy()
    df["top_3"] = df["top_3"].apply(lambda x: zfill_num(x, 3))
    df["bottom_2"] = df["bottom_2"].apply(lambda x: zfill_num(x, 2))
    df["weekday_en"] = df["dt"].dt.day_name()
    return df


def save_history(df):
    out = df.copy()
    for col in ["dt", "weekday_en"]:
        if col in out.columns:
            out = out.drop(columns=[col])
    out.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")


def get_transformations(top_3_str, bottom_2_str="00"):
    t3 = zfill_num(top_3_str, 3)
    b2 = zfill_num(bottom_2_str, 2)
    a, b, c = [int(x) for x in t3]
    d, e = [int(x) for x in b2]

    digits = [a, b, c, d, e]
    carry = {str(x) for x in digits}
    pm1 = {str((x + delta) % 10) for x in digits for delta in (-1, 1)}

    sum_t3 = (a + b + c) % 10
    sum_b2 = (d + e) % 10
    sum_total = (sum_t3 + sum_b2) % 10
    sum_formulas = {str(sum_t3), str(sum_b2), str(sum_total)}

    cross_formulas = {
        str((b + e) % 10),
        str((c + d) % 10),
        str((a + d) % 10),
        str((a + e) % 10),
    }

    rotations = {t3[1:] + t3[0], t3[2] + t3[:2]}
    mirror_map = {0: 5, 1: 6, 2: 7, 3: 8, 4: 9, 5: 0, 6: 1, 7: 2, 8: 3, 9: 4}
    mirror = "".join(str(mirror_map[int(x)]) for x in t3)
    shifted = "".join(str((int(x) + 2) % 10) for x in t3)
    doubles = {x * 2 for x in t3}
    sandwiches = {
        a_str + b_str + a_str for a_str in t3 for b_str in t3 if a_str != b_str
    }

    return {
        "carry_over": carry,
        "pm1": pm1,
        "sum_formulas": sum_formulas,
        "cross_formulas": cross_formulas,
        "rotations": rotations,
        "mirror": mirror,
        "shifted": shifted,
        "doubles": doubles,
        "sandwiches": sandwiches,
    }


def daily_number_for_day(day, history=None):
    # ล็อกให้ใช้ค่าจาก DEFAULT_DAILY_NUMBERS เสมอตามที่คุณต้องการ
    return DEFAULT_DAILY_NUMBERS.get(day, "000000")


def formula_candidates(base_t3, base_b2, next_day, history=None):
    trans = get_transformations(base_t3, base_b2)
    daily = daily_number_for_day(next_day, history)

    candidates = defaultdict(set)
    candidates["Carry Over"].update(trans["carry_over"])
    candidates["±1"].update(trans["pm1"])
    candidates["Sum Modulo"].update(trans["sum_formulas"])
    candidates["Cross Sum"].update(trans["cross_formulas"])
    candidates["Daily 6-Digit"].update(daily)
    candidates["Rotation"].update(set("".join(trans["rotations"])))
    candidates["Mirror"].update(trans["mirror"])
    candidates["Shift +2"].update(trans["shifted"])
    candidates["Double"].update(set("".join(trans["doubles"])))
    candidates["Sandwich"].update(set("".join(trans["sandwiches"])))
    return candidates, daily, trans


def evaluate_formula(formula, trans, daily, actual_t3, actual_b2):
    t3 = zfill_num(actual_t3, 3)
    b2 = zfill_num(actual_b2, 2)

    if formula == "Carry Over":
        digits = trans["carry_over"]
        return int(any(d in t3 for d in digits)), int(any(d in b2 for d in digits))
    if formula == "±1":
        digits = trans["pm1"]
        return int(any(d in t3 for d in digits)), int(any(d in b2 for d in digits))
    if formula == "Sum Modulo":
        digits = trans["sum_formulas"]
        return int(any(d in t3 for d in digits)), int(any(d in b2 for d in digits))
    if formula == "Cross Sum":
        digits = trans["cross_formulas"]
        return int(any(d in t3 for d in digits)), int(any(d in b2 for d in digits))
    if formula == "Daily 6-Digit":
        return int(any(d in t3 for d in daily)), int(any(d in b2 for d in daily))
    if formula == "Rotation":
        rots = trans["rotations"]
        return int(any(r == t3 for r in rots)), int(
            any(set(b2).issubset(set(r)) for r in rots)
        )
    if formula == "Mirror":
        return int(any(d in t3 for d in trans["mirror"])), int(
            any(d in b2 for d in trans["mirror"])
        )
    if formula == "Shift +2":
        return int(any(d in t3 for d in trans["shifted"])), int(
            any(d in b2 for d in trans["shifted"])
        )
    if formula == "Double":
        return int(any(t3[i] == t3[i + 1] for i in range(2))), int(b2[0] == b2[1])
    if formula == "Sandwich":
        return int(t3[0] == t3[2] or t3[0] == t3[1] or t3[1] == t3[2]), 0
    return 0, 0


def exact_pattern_score(formula, trans, daily, actual_t3, actual_b2):
    t3 = zfill_num(actual_t3, 3)
    b2 = zfill_num(actual_b2, 2)

    if formula == "Rotation":
        if t3 in trans["rotations"]:
            return 1.0, 1.0
    if formula == "Mirror":
        return float(t3 == trans["mirror"]), float(b2 == trans["mirror"][-2:])
    if formula == "Shift +2":
        return float(t3 == trans["shifted"]), float(b2 == trans["shifted"][-2:])
    if formula == "Daily 6-Digit":
        return len(set(t3) & set(daily)) / 3.0, len(set(b2) & set(daily)) / 2.0
    return 0.0, 0.0


def backtest_dataframe(df):
    if len(df) < 2:
        return pd.DataFrame()

    rows = []
    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        actual = df.iloc[i]
        day = actual["weekday_en"]
        daily = daily_number_for_day(day, df.iloc[:i])
        trans = get_transformations(prev["top_3"], prev["bottom_2"])

        for formula in FORMULAS:
            hit3, hit2 = evaluate_formula(
                formula, trans, daily, actual["top_3"], actual["bottom_2"]
            )
            exact3, exact2 = exact_pattern_score(
                formula, trans, daily, actual["top_3"], actual["bottom_2"]
            )
            rows.append(
                {
                    "date": actual["date"],
                    "weekday": day,
                    "formula": formula,
                    "hit_3d": hit3,
                    "hit_2d": hit2,
                    "exact_3d": exact3,
                    "exact_2d": exact2,
                }
            )
    return pd.DataFrame(rows)


def formula_ranking(df):
    bt = backtest_dataframe(df)
    if bt.empty:
        return pd.DataFrame()

    result = []
    for formula in FORMULAS:
        x = bt[bt["formula"] == formula]
        n = len(x)
        hit3 = x["hit_3d"].sum()
        hit2 = x["hit_2d"].sum()
        avg_exact3 = x["exact_3d"].mean()
        avg_exact2 = x["exact_2d"].mean()
        composite = (
            0.40 * (hit3 / n)
            + 0.35 * (hit2 / n)
            + 0.15 * avg_exact3
            + 0.10 * avg_exact2
        ) * 100
        result.append(
            {
                "Formula": formula,
                "N": n,
                "3D Hit%": round(hit3 / n * 100, 1),
                "2D Hit%": round(hit2 / n * 100, 1),
                "3D Exact%": round(avg_exact3 * 100, 1),
                "2D Exact%": round(avg_exact2 * 100, 1),
                "Composite": round(composite, 1),
            }
        )
    return (
        pd.DataFrame(result)
        .sort_values("Composite", ascending=False)
        .reset_index(drop=True)
    )


def dynamic_weights(df):
    ranking = formula_ranking(df)
    if ranking.empty:
        return {f: 1.0 for f in FORMULAS}

    weights = {}
    for _, row in ranking.iterrows():
        w = 0.5 + row["Composite"] / 50.0
        weights[row["Formula"]] = max(0.5, min(3.0, w))
    return weights


def digit_scores(df, next_day):
    if df.empty:
        return {str(i): 0.0 for i in range(10)}, {}, "000000"

    latest = df.iloc[-1]
    candidates, daily, trans = formula_candidates(
        latest["top_3"], latest["bottom_2"], next_day, df
    )
    weights = dynamic_weights(df)
    scores = {str(i): 0.0 for i in range(10)}

    for formula in FORMULAS:
        w = weights.get(formula, 1.0)
        for digit in candidates[formula]:
            scores[str(digit)] += w

    recent = df.tail(min(20, len(df)))
    freq = Counter()
    for _, row in recent.iterrows():
        freq.update(row["top_3"])
        freq.update(row["bottom_2"])
    for d, n in freq.items():
        scores[d] += min(1.0, n / max(10, len(recent) * 3))

    return scores, weights, daily


def generate_prediction(df, next_day):
    if df.empty:
        return None

    latest = df.iloc[-1]
    scores, weights, daily = digit_scores(df, next_day)
    ordered = sorted(scores, key=lambda d: (-scores[d], d))
    den = ordered[0]
    rong = ordered[1:4]
    kan = ordered[4:7]

    pairs = []
    for r in rong:
        pairs.extend([den + r, r + den])
    pairs = list(dict.fromkeys(pairs))

    top4 = ordered[:4]
    triples = []
    for a in top4:
        for b in top4:
            for c in top4:
                if len({a, b, c}) >= 2:
                    triples.append(a + b + c)
    triples = sorted(
        set(triples), key=lambda x: -(scores[x[0]] + scores[x[1]] + scores[x[2]])
    )[:12]

    doubles = [d + d for d in ordered[:4]]
    sandwiches = [a + b + a for a in ordered[:4] for b in ordered[:4] if a != b][:8]

    return {
        "latest": latest,
        "daily": daily,
        "scores": scores,
        "ordered": ordered,
        "den": den,
        "rong": rong,
        "kan": kan,
        "pairs": pairs,
        "triples": triples,
        "doubles": doubles,
        "sandwiches": sandwiches,
        "weights": weights,
    }


# ================================================================
# STREAMLIT UI
# ================================================================

initialize_csv()

st.title("🎯 HANOI AI PROFESSIONAL v2.0")
st.caption("Dynamic Backtest + Formula Accuracy + Weighted Prediction")

# Sidebar: จัดการไฟล์ CSV
with st.sidebar:
    st.header("💾 จัดการฐานข้อมูล CSV")
    st.info(
        "บน Streamlit Cloud ข้อมูลจะรีเซ็ตเมื่อแอปหลับ แนะนำให้กดดาวน์โหลด CSV ไว้สำรอง"
    )

    df_current = load_history().sort_values("dt", ascending=False)
    csv_bytes = (
        df_current.drop(columns=["dt", "weekday_en"], errors="ignore")
        .to_csv(index=False)
        .encode("utf-8-sig")
    )
    st.download_button(
        label="⬇️ ดาวน์โหลดไฟล์ประวัติ (CSV)",
        data=csv_bytes,
        file_name="history_hanoi.csv",
        mime="text/csv",
        use_container_width=True,
    )

    uploaded_file = st.file_uploader("⬆️ อัปโหลดไฟล์ประวัติเดิม (.csv)", type=["csv"])
    if uploaded_file is not None:
        if st.button("นำเข้าข้อมูลจากไฟล์ที่อัปโหลด", use_container_width=True):
            try:
                up_df = pd.read_csv(uploaded_file, dtype=str).fillna("")
                required = ["date", "special", "first_prize", "top_3", "bottom_2"]
                if all(col in up_df.columns for col in required):
                    up_df["dt"] = up_df["date"].apply(parse_thai_date)
                    up_df = up_df.dropna(subset=["dt"]).sort_values(
                        "dt", ascending=False
                    )
                    save_history(up_df)
                    st.success("✅ นำเข้าข้อมูลเรียบร้อยแล้ว!")
                    st.rerun()
                else:
                    st.error("⚠️ รูปแบบคอลัมน์ในไฟล์ CSV ไม่ถูกต้อง")
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

df_desc = load_history().sort_values("dt", ascending=False).reset_index(drop=True)
df_asc = df_desc.sort_values("dt", ascending=True).reset_index(drop=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🔮 ทำนายงวดถัดไป",
        "➕ อัปเดต / ลบข้อมูล",
        "📊 สถิติ & Backtest",
        "📜 ประวัติผลรางวัล",
        "📅 เลขประจำวัน (Daily)",
    ]
)

# ---------------- TAB 1 ----------------
with tab1:
    if df_asc.empty:
        st.warning("⚠️ ยังไม่มีข้อมูลในระบบ กรุณาเพิ่มข้อมูลที่แท็บ 'อัปเดต / ลบข้อมูล'")
    else:
        latest_row = df_asc.iloc[-1]
        days_list = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        col_sel, col_info = st.columns([1, 2])
        with col_sel:
            selected_day = st.selectbox(
                "เลือกวันของงวดถัดไป", days_list, index=0
            )
        with col_info:
            st.info(
                f"**ฐานข้อมูลล่าสุด:** วันที่ `{latest_row['date']}` ({latest_row['weekday_en']}) | "
                f"3 ตัวบน: **`{latest_row['top_3']}`** | 2 ตัวล่าง: **`{latest_row['bottom_2']}`**"
            )

        pred = generate_prediction(df_asc, selected_day)

        st.subheader(f"ผลการวิเคราะห์ประจำวัน {selected_day} (Daily: {pred['daily']})")

        m1, m2, m3 = st.columns(3)
        m1.metric("🎯 เลขเด่น", pred["den"], f"Score: {pred['scores'][pred['den']]:.2f}")
        m2.metric("🥈 เลขรอง", " - ".join(pred["rong"]))
        m3.metric("🛡️ เลขกัน", " - ".join(pred["kan"]))

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🔢 ชุด 2 ตัว (เน้นไป-กลับ)")
            st.success(" , ".join(pred["pairs"]))
            st.markdown("#### 👯 ชุดเบิ้ล / หาม")
            st.write(f"**เบิ้ล:** {', '.join(pred['doubles'])}")
            st.write(f"**หาม:** {', '.join(pred['sandwiches'])}")
        with c2:
            st.markdown("#### 🎰 ชุด 3 ตัว AI (คัด 10 อันดับแรก)")
            st.info(" , ".join(pred["triples"][:10]))

        with st.expander("⚖️ ดูค่าน้ำหนักสูตร (Dynamic Formula Weights) & คะแนนรายตัวเลข"):
            wc1, wc2 = st.columns(2)
            with wc1:
                w_df = pd.DataFrame(
                    [
                        {"Formula": k, "Weight": round(v, 2)}
                        for k, v in sorted(
                            pred["weights"].items(), key=lambda x: x[1], reverse=True
                        )
                    ]
                )
                st.dataframe(w_df, use_container_width=True, hide_index=True)
            with wc2:
                s_df = pd.DataFrame(
                    [
                        {"Digit": d, "Total Score": round(pred["scores"][d], 2)}
                        for d in pred["ordered"]
                    ]
                )
                st.bar_chart(s_df.set_index("Digit"))

# ---------------- TAB 2 ----------------
with tab2:
    col_add, col_del = st.columns([3, 2])
    with col_add:
        st.subheader("➕ บันทึกผลรางวัลใหม่")
        with st.form("add_result_form", clear_on_submit=True):
            f_date = st.text_input("วันที่ (DD/MM/YYYY พ.ศ.)", placeholder="เช่น 06/10/2569")
            f_special = st.text_input("รางวัลพิเศษ (5 หลัก)", max_chars=5)
            f_first = st.text_input("รางวัลที่ 1 (5 หลัก)", max_chars=5)
            f_top3 = st.text_input("เลข 3 ตัวบน (3 หลัก)", max_chars=3)
            f_bot2 = st.text_input("เลข 2 ตัวล่าง (2 หลัก)", max_chars=2)
            submitted = st.form_submit_button("💾 บันทึกข้อมูล", use_container_width=True)

            if submitted:
                parsed_dt = parse_thai_date(f_date)
                if pd.isna(parsed_dt):
                    st.error("⚠️ รูปแบบวันที่ไม่ถูกต้อง กรุณากรอกเป็น DD/MM/YYYY")
                elif not f_top3.strip() or not f_bot2.strip():
                    st.error("⚠️ กรุณากรอกเลข 3 ตัวบน และ 2 ตัวล่างให้ครบถ้วน")
                else:
                    new_row = pd.DataFrame(
                        [
                            {
                                "date": f_date.strip(),
                                "special": f_special.strip(),
                                "first_prize": f_first.strip(),
                                "top_3": zfill_num(f_top3, 3),
                                "bottom_2": zfill_num(f_bot2, 2),
                            }
                        ]
                    )
                    raw = df_desc.drop(columns=["dt", "weekday_en"], errors="ignore")
                    raw = pd.concat([new_row, raw], ignore_index=True)
                    raw = raw.drop_duplicates(subset=["date"], keep="first")
                    raw["dt"] = raw["date"].apply(parse_thai_date)
                    raw = raw.sort_values("dt", ascending=False)
                    save_history(raw)
                    st.success(f"✅ บันทึกผลรางวัลงวดวันที่ {f_date.strip()} สำเร็จ!")
                    st.rerun()

    with col_del:
        st.subheader("🗑️ ลบข้อมูลงวดล่าสุด")
        if not df_desc.empty:
            st.write("รายการล่าสุด 5 งวด:")
            st.dataframe(
                df_desc[["date", "top_3", "bottom_2"]].head(5),
                use_container_width=True,
                hide_index=True,
            )
            latest_date = df_desc.iloc[0]["date"]
            if st.button(
                f"ลบงวดล่าสุด ({latest_date})", type="primary", use_container_width=True
            ):
                updated_df = df_desc.iloc[1:].copy()
                save_history(updated_df)
                st.success(f"✅ ลบข้อมูลงวดวันที่ {latest_date} เรียบร้อยแล้ว")
                st.rerun()
        else:
            st.info("ไม่มีข้อมูลให้ลบ")

# ---------------- TAB 3 ----------------
with tab3:
    st.subheader("📊 Formula Ranking / Backtest")
    if len(df_asc) < 2:
        st.warning("⚠️ ข้อมูลไม่เพียงพอสำหรับการทำ Backtest")
    else:
        ranking_df = formula_ranking(df_asc)
        st.dataframe(ranking_df, use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("🔍 Backtest Detail (ย้อนหลัง 10 งวดล่าสุด)")
        bt_df = backtest_dataframe(df_asc)
        recent_bt = bt_df.tail(len(FORMULAS) * min(10, max(1, len(df_asc) - 1)))
        st.dataframe(recent_bt, use_container_width=True, hide_index=True)

# ---------------- TAB 4 ----------------
with tab4:
    st.subheader(f"📜 ประวัติผลรางวัลทั้งหมด ({len(df_desc)} งวด)")
    cols = ["date", "weekday_en", "special", "first_prize", "top_3", "bottom_2"]
    st.dataframe(df_desc[cols], use_container_width=True, hide_index=True)

# ---------------- TAB 5 ----------------
with tab5:
    st.subheader("📅 ชุดเลขประจำวัน (Daily 6-Digit)")
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    daily_rows = []
    for d in days:
        daily_rows.append(
            {
                "Day": d,
                "Fixed Number": DEFAULT_DAILY_NUMBERS[d],
            }
        )
    st.dataframe(pd.DataFrame(daily_rows), use_container_width=True, hide_index=True)
    st.info("สถานะปัจจุบัน: ใช้ชุดเลขประจำวันแบบค่าคงที่ตามที่คุณตั้งค่าไว้ในระบบเรียบร้อยแล้ว")
