import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import io
import base64
from PIL import Image
import time

# ================= SESSION =================
if "gps" not in st.session_state:
    st.session_state.gps = ""
if "login" not in st.session_state:
    st.session_state.login = False

# ================= PHOTO LOGIC (BASE64) =================
def upload_foto(file):
    if file is None: return ""
    try:
        img = Image.open(file)
        img.thumbnail((400, 400)) # Kompres agar tidak berat
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=70)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        st.error(f"Gagal memproses foto: {e}")
        return ""

# ================= CONFIG =================
st.set_page_config(
    page_title="E-Kinerja KPU Kota Bengkulu",
    page_icon="📊",
    layout="wide"
)

# ================= UI CUSTOM (SIDEBAR FIX) =================
st.markdown("""
<style>
[data-testid="stSidebar"] {background:#0f172a;}
[data-testid="stSidebar"] * {color:white !important;}
/* Memaksa input di sidebar agar teksnya HITAM dan kotak PUTIH */
[data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea {
    color: black !important;
    background-color: white !important;
}
.stButton button {background:#ef4444;color:white;border-radius:8px;}
.card {padding:15px;border-radius:12px;color:white;text-align:center;}
.c1{background:#ef4444;} .c2{background:#22c55e;}
.c3{background:#f59e0b;} .c4{background:#3b82f6;}
</style>
""", unsafe_allow_html=True)

# ================= GOOGLE CONNECT =================
@st.cache_resource
def connect():
    info = dict(st.secrets["connections"]["gsheets"])
    info["private_key"] = info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(
        info, 
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ],
    )
    return gspread.authorize(creds).open_by_key(st.secrets["SPREADSHEET_ID"])

spreadsheet = connect()
sheet = spreadsheet.sheet1
user_sheet = spreadsheet.worksheet("users")

# ================= HELPER =================
def safe(x): return "" if x is None else str(x)

def load_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df["row"] = range(2, len(df)+2)
    return df

def load_users():
    return pd.DataFrame(user_sheet.get_all_records())

def parse_jam(x):
    try:
        h,m = str(x).replace(".",":").split(":")
        return int(h)*60 + int(m)
    except: return None

def hitung_durasi(masuk, keluar):
    jm = parse_jam(masuk)
    jk = parse_jam(keluar)
    if jm is not None and jk is not None and jk > jm:
        return round((jk-jm)/60, 2)
    return 0

# ================= LOGIN =================
users = load_users()
if not st.session_state.login:
    st.title("🔐 Login E-Kinerja KPU Kota Bengkulu")
    nip = st.text_input("NIP")
    pw = st.text_input("Password", type="password")
    if st.button("Login"):
        cek = users[(users["NIP"].astype(str)==str(nip)) & (users["Password"].astype(str)==str(pw))]
        if not cek.empty:
            u = cek.iloc[0]
            st.session_state.login=True
            st.session_state.nama=u["Nama"]
            st.session_state.nip=str(u["NIP"])
            st.session_state.jabatan=u["Jabatan"]
            st.session_state.role=u["Role"]
            st.rerun()
        else: st.error("NIP atau Password salah!")
    st.stop()

# ================= SIDEBAR & MENU =================
st.sidebar.title(f"👤 {st.session_state.nama}")
menu = st.sidebar.radio("Menu", ["Dashboard", "Input", "Data Kinerja", "Admin"])

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# --- SATU-SATUNYA LOGIKA EDIT (DI SIDEBAR) ---
if "edit" in st.session_state:
    ed = st.session_state.edit
    st.sidebar.divider()
    st.sidebar.subheader("✏️ Edit Data")
    
    with st.sidebar.container():
        st.sidebar.info(f"Mengedit baris: {ed['row']}")
        new_masuk = st.sidebar.text_input("Jam Masuk", value=safe(ed.get("Jam Masuk", "")))
        new_keluar = st.sidebar.text_input("Jam Keluar", value=safe(ed.get("Jam Keluar", "")))
        new_uraian = st.sidebar.text_area("Uraian", value=safe(ed.get("Uraian", "")), height=150)
        new_output = st.sidebar.text_area("Output", value=safe(ed.get("Output", "")), height=150)

        col1, col2 = st.sidebar.columns(2)
        if col1.button("Update ✅", key="upd_sidebar"):
            dur = hitung_durasi(new_masuk, new_keluar)
            try:
                row_idx = int(ed['row'])
                sheet.update(f"E{row_idx}:J{row_idx}", 
                             [[new_masuk, new_keluar, dur, new_uraian, new_output, ed.get("Lokasi","")]])
                st.sidebar.success("Berhasil diupdate!")
                del st.session_state.edit
                time.sleep(1)
                st.rerun()
            except Exception as e: st.sidebar.error(f"Gagal: {e}")
        
        if col2.button("Batal ❌", key="can_sidebar"):
            del st.session_state.edit
            st.rerun()

# ================= DASHBOARD =================
if menu == "Dashboard":
    st.subheader("📊 Dashboard Kinerja")
    df = load_data()
    if not df.empty:
        df["Durasi"] = df.apply(lambda r: hitung_durasi(r["Jam Masuk"], r["Jam Keluar"]), axis=1)
        df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')
        tgl = st.date_input("Range Tanggal", value=(df["Tanggal"].min(), df["Tanggal"].max()))
        if len(tgl)==2:
            df = df[(df["Tanggal"]>=pd.to_datetime(tgl[0])) & (df["Tanggal"]<=pd.to_datetime(tgl[1]))]
        
        c1,c2,c3,c4 = st.columns(4)
        c1.markdown(f"<div class='card c1'><h3>{len(df)}</h3>Laporan</div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='card c2'><h3>{df['Durasi'].sum():.2f}</h3>Jam</div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='card c3'><h3>{df['Tanggal'].nunique()}</h3>Hari</div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='card c4'><h3>{df['Nama'].nunique()}</h3>Pegawai</div>", unsafe_allow_html=True)

# ================= INPUT =================
elif menu == "Input":
    st.subheader("📍 Input Kinerja Harian")
    lokasi = st.selectbox("Lokasi", ["Kantor", "Rumah", "Dinas Luar / SPT"])
    
    foto = None
    koordinat = ""
    if lokasi == "Rumah":
        foto = st.camera_input("Ambil Foto WFH")
        from streamlit_js_eval import get_geolocation
        loc = get_geolocation()
        if loc:
            koordinat = f"{loc['coords']['latitude']}, {loc['coords']['longitude']}"
            st.success(f"GPS Terdeteksi: {koordinat}")
    
    tgl = st.date_input("Tanggal Kegiatan", date.today())
    masuk = st.text_input("Jam Masuk", "07:30")
    keluar = st.text_input("Jam Keluar", "16:00")
    uraian = st.text_area("Uraian Kegiatan (Bisa Enter)")
    output = st.text_area("Output/Hasil (Bisa Enter)")

    if st.button("🚀 Simpan Laporan", type="primary"):
        dur = hitung_durasi(masuk, keluar)
        if not uraian or not output:
            st.error("Uraian dan Output tidak boleh kosong!")
        else:
            link_foto = upload_foto(foto) if lokasi == "Rumah" else ""
            sheet.append_row([st.session_state.nama, st.session_state.nip, st.session_state.jabatan, tgl.strftime("%Y-%m-%d"), masuk, keluar, dur, uraian, output, lokasi, koordinat, link_foto])
            st.success("Data berhasil disimpan!")
            time.sleep(1)
            st.rerun()

# ================= DATA KINERJA =================
elif menu == "Data Kinerja":
    st.subheader("📋 Daftar Laporan Kinerja")
    df = load_data()
    if df.empty: st.info("Belum ada data"); st.stop()
    
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')
    if st.session_state.role not in ["admin","pimpinan"]:
        df = df[df["NIP"].astype(str)==st.session_state.nip]

    for i, row in df.iterrows():
        with st.container():
            c1, c2, c3, c4 = st.columns([5,2,1,1])
            c1.write(f"**{row['Nama']}** - {row['Tanggal'].date()}")
            c1.caption(f"Kegiatan: {row['Uraian']}")
            if row.get("Output"): c1.markdown(f"**Output:** \n{row['Output']}")
            if row.get("Foto") and str(row["Foto"]).startswith("data:image"):
                c1.image(row["Foto"], width=250, caption="Dokumentasi")
            
            c2.write(f"⏱ {row['Durasi']} jam")
            if c3.button("✏️", key=f"edit{i}"):
                st.session_state.edit = row
                st.rerun()
            if c4.button("🗑", key=f"del{i}"):
                sheet.delete_rows(int(row["row"]))
                st.rerun()
            st.divider()

# ================= ADMIN =================
elif menu == "Admin":
    if st.session_state.role != "admin": st.error("Akses Ditolak!"); st.stop()
    st.subheader("👥 Manajemen User")
    # (Kode admin tetap sama seperti versi Anda)
    nip_a = st.text_input("NIP Baru")
    nama_a = st.text_input("Nama Baru")
    jab_a = st.text_input("Jabatan Baru")
    pw_a = st.text_input("Password")
    rol_a = st.selectbox("Role", ["pegawai", "admin", "pimpinan"])
    if st.button("Tambah User"):
        user_sheet.append_row([nip_a, nama_a, jab_a, pw_a, rol_a])
        st.success("User Berhasil Ditambah!")