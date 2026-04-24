import streamlit as st
import pandas as pd
from datetime import datetime, time
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIG ---
st.set_page_config(page_title="Aplikasi Kinerja KPU", layout="wide")
st.title("📊 Aplikasi Kinerja Harian KPU")

# --- GOOGLE SHEETS SETUP ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/16l6pcqA1CvM-8P5rsT37UkMJnrEWTJW1CcOcS92WnlM"
WORKSHEET_NAME = "Sheet1"

# --- AUTH ---
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["connections"]["gsheets"]["service_account"],
    scopes=scope
)

# DEBUG (boleh dihapus nanti kalau sudah jalan)
st.write("Service Account:", creds.service_account_email)

client = gspread.authorize(creds)

# Ambil spreadsheet & sheet
spreadsheet = client.open_by_url(SPREADSHEET_URL)
sheet = spreadsheet.sheet1  # lebih aman daripada worksheet("Sheet1")

# --- LOAD DATA ---
@st.cache_data(ttl=60)
def load_data():
    try:
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

existing_data = load_data()

# --- FORM INPUT ---
with st.form("form_kinerja"):

    col1, col2 = st.columns(2)

    with col1:
        nama = st.text_input("Nama")
        nip = st.text_input("NIP")
        jabatan = st.text_input("Jabatan")

    with col2:
        tanggal = st.date_input("Tanggal", datetime.today())
        jam_masuk = st.time_input("Jam Masuk", value=time(8, 0))
        jam_keluar = st.time_input("Jam Keluar", value=time(17, 0))

    st.markdown("### 📝 Uraian Pekerjaan")
    uraian = st.text_area(
        "Isi uraian pekerjaan (gunakan ENTER untuk baris baru)",
        height=150
    )

    st.markdown("### 📦 Output Pekerjaan")
    output = st.text_area(
        "Isi output pekerjaan (gunakan ENTER untuk baris baru)",
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

    if nama.strip() == "" or nip.strip() == "":
        st.warning("⚠️ Nama dan NIP wajib diisi!")
    else:
        new_data = pd.DataFrame([{
            "Nama": nama,
            "NIP": nip,
            "Jabatan": jabatan,
            "Tanggal": tanggal.strftime("%Y-%m-%d"),
            "Jam Masuk": jam_masuk.strftime("%H:%M"),
            "Jam Keluar": jam_keluar.strftime("%H:%M"),
            "Uraian Pekerjaan": uraian,
            "Output Pekerjaan": output,
            "Lokasi Bekerja": lokasi
        }])

        try:
            # Jika sheet kosong
            if existing_data.empty:
                updated_df = new_data
            else:
                updated_df = pd.concat([existing_data, new_data], ignore_index=True)

            # Update ke Google Sheets
            sheet.update(
                [updated_df.columns.values.tolist()] +
                updated_df.values.tolist()
            )

            st.success("✅ Data berhasil disimpan!")
            st.cache_data.clear()
            st.rerun()

        except Exception as e:
            st.error(f"❌ Gagal menyimpan data: {e}")

# --- TAMPILKAN DATA ---
st.markdown("## 📋 Data Kinerja")

if not existing_data.empty:
    st.dataframe(existing_data, use_container_width=True)
else:
    st.info("Belum ada data.")