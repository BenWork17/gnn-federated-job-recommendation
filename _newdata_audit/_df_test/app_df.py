
import pandas as pd
import streamlit as st

st.title("Test dataframe")

rows = [
    {"yeu cau": "A", "cach do": "x", "thuc do": "1", "ket luan": "Dat"},
    {"yeu cau": "B", "cach do": "y", "thuc do": "2", "ket luan": "Chua"},
    {"yeu cau": "C", "cach do": "z", "thuc do": "3", "ket luan": "Dat"},
]
tbl = pd.DataFrame(rows)

def _to_mau(row):
    mau = ("color:#1e8449;font-weight:700" if row["ket luan"] == "Dat"
           else "color:#a93226;font-weight:700")
    return ["" if c != "ket luan" else mau for c in row.index]

st.subheader("1. Styler + use_container_width (cach hien tai)")
st.dataframe(tbl.style.apply(_to_mau, axis=1), use_container_width=True, hide_index=True)

st.subheader("2. Styler + width=stretch (cach moi)")
st.dataframe(tbl.style.apply(_to_mau, axis=1), width="stretch", hide_index=True)

st.subheader("3. DataFrame thuong + width=stretch")
st.dataframe(tbl, width="stretch", hide_index=True)

st.subheader("4. st.table")
st.table(tbl)
