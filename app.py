import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIG ---
st.set_page_config(page_title="Aplikasi Kinerja KPU", layout="wide")
st.title("📊 Aplikasi Kinerja Harian KPU")

# --- KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# ✅ PAKAI URL ASLI (BUKAN CSV)
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/16l6pcqA1CvM-8P5rsT37UkMJnrEWTJW1CcOcS92WnlM"
WORKSHEET_NAME = "Sheet1"  # ganti kalau nama sheet beda

# --- FUNGSI LOAD DATA ---
@st.cache_data(ttl=60)
def load_data():
    try:
        df = conn.read(
            spreadsheet=SPREADSHEET_URL,
            worksheet=WORKSHEET_NAME
        )
        return df
    except Exception as e:
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

    if nama.strip() == "" or nip.strip() == "":
        st.warning("⚠️ Nama dan NIP wajib diisi!")
    else:
        new_data = pd.DataFrame([{
            "Nama": nama,
            "NIP": nip,
            "Jabatan": jabatan,
            "Tanggal": tanggal.strftime("%Y-%m-%d"),
            "Jam Masuk": jam_masuk,
            "Jam Keluar": jam_keluar,
            "Uraian Pekerjaan": uraian,
            "Output Pekerjaan": output,
            "Lokasi Bekerja": lokasi
        }])

        try:
            # Gabungkan data
            if existing_data.empty:
                updated_df = new_data
            else:
                updated_df = pd.concat([existing_data, new_data], ignore_index=True)

            # ✅ UPDATE KE GOOGLE SHEETS
            conn.update(
                spreadsheet=SPREADSHEET_URL,
                worksheet=WORKSHEET_NAME,
                data=updated_df
            )

            st.success("✅ Data berhasil disimpan!")
            st.cache_data.clear()  # refresh cache
            st.rerun()

        except Exception as e:
            st.error(f"❌ Gagal menyimpan data: {e}")

# --- TAMPILKAN DATA ---
st.markdown("## 📋 Data Kinerja")

if not existing_data.empty:
    st.dataframe(existing_data, use_container_width=True)
else:
    st.info("Belum ada data.")