import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Aplikasi Kinerja KPU", layout="wide")

st.title("📊 Aplikasi Kinerja Harian KPU")

# --- KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# ⚠️ PAKAI FORMAT CSV (WAJIB)
url = "https://docs.google.com/spreadsheets/d/16l6pcqA1CvM-8P5rsT37UkMJnrEWTJW1CcOcS92WnlM/export?format=csv"

# --- AMBIL DATA LAMA (ANTI ERROR) ---
try:
    existing_data = conn.read(spreadsheet=url)
except:
    existing_data = pd.DataFrame()

# --- FORM INPUT ---
with st.form("form_kinerja"):

    col1, col2 = st.columns(2)

    with col1:
        nama = st.text_input("Nama")
        nip = st.text_input("NIP")
        jabatan = st.text_input("Jabatan")

    with col2:
        tanggal = st.date_input("Tanggal", datetime.today())
        jam_masuk = st.time_input("Jam Masuk")
        jam_keluar = st.time_input("Jam Keluar")

    st.markdown("### 📝 Uraian Pekerjaan")
    uraian = st.text_area(
        "Isi uraian pekerjaan (bisa ENTER untuk baris baru)",
        height=150
    )

    st.markdown("### 📦 Output Pekerjaan")
    output = st.text_area(
        "Isi output pekerjaan (bisa ENTER untuk baris baru)",
        height=150
    )

    st.markdown("### 📍 Lokasi Bekerja")
    lokasi = st.radio(
        "Pilih lokasi bekerja:",
        ["Kantor", "Rumah", "Surat Tugas / Perjalanan Dinas"],
        horizontal=True
    )

    submit = st.form_submit_button("💾 Simpan Data")

# --- SIMPAN DATA ---
if submit:

    if nama == "" or nip == "":
        st.warning("Nama dan NIP wajib diisi!")
    else:
        new_data = pd.DataFrame([{
            "Nama": nama,
            "NIP": nip,
            "Jabatan": jabatan,
            "Tanggal": tanggal.strftime("%Y-%m-%d"),
            "Jam Masuk": str(jam_masuk),
            "Jam Keluar": str(jam_keluar),
            "Uraian Pekerjaan": uraian,
            "Output Pekerjaan": output,
            "Lokasi Bekerja": lokasi
        }])

        # Gabungkan dengan data lama
        if existing_data.empty:
            updated_df = new_data
        else:
            updated_df = pd.concat([existing_data, new_data], ignore_index=True)

        # Simpan ke Google Sheets
        conn.update(spreadsheet=url, data=updated_df)

        st.success("✅ Data berhasil disimpan!")

# --- TAMPILKAN DATA ---
st.markdown("## 📋 Data Kinerja")

if not existing_data.empty:
    st.dataframe(existing_data, use_container_width=True)
else:
    st.info("Belum ada data.")