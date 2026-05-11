import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import io
import base64
from PIL import Image
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ================= SESSION =================
if "gps" not in st.session_state:
    st.session_state.gps = ""
if "login" not in st.session_state:
    st.session_state.login = False

# ================= DRIVE & PHOTO =================
def upload_foto(file):
    if file is None: return ""
    try:
        img = Image.open(file)
        img.thumbnail((400, 400))
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

# ================= UI CUSTOM =================
st.markdown("""
<style>
[data-testid="stSidebar"] {background:#0f172a;}
[data-testid="stSidebar"] * {color:white !important;}
/* Memaksa teks input di sidebar agar terlihat jelas */
[data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea {
    color: #0f172a !important; 
    background-color: white !important;
}
.stButton button {background:#ef4444;color:white;border-radius:8px;}
.card {padding:15px;border-radius:12px;color:white;text-align:center;}
.c1{background:#ef4444;} .c2{background:#22c55e;}
.c3{background:#f59e0b;} .c4{background:#3b82f6;}
</style>
""", unsafe_allow_html=True)

# ================= GOOGLE =================
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
    df = pd.DataFrame(sheet.get_all_records())
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

# ================= LOGIN LOGIC =================
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
        else: st.error("Login gagal")
    st.stop()

# ================= SIDEBAR =================
st.sidebar.title(f"👤 {st.session_state.nama}")
menu = st.sidebar.radio("Menu", ["Dashboard", "Input", "Data Kinerja", "Admin"])

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# --- SATU-SATUNYA BLOK EDIT (DI SIDEBAR) ---
if "edit" in st.session_state:
    ed = st.session_state.edit
    st.sidebar.divider()
    st.sidebar.subheader("✏️ Edit Data")
    
    # Form Input di Sidebar
    with st.sidebar.container():
        new_masuk = st.text_input("Jam Masuk", value=safe(ed.get("Jam Masuk", "07:30")), key="sb_masuk")
        new_keluar = st.text_input("Jam Keluar", value=safe(ed.get("Jam Keluar", "16:00")), key="sb_keluar")
        new_uraian = st.text_area("Uraian", value=safe(ed.get("Uraian", "")), key="sb_uraian")
        new_output = st.text_area("Output", value=safe(ed.get("Output", "")), key="sb_output")

        c1, c2 = st.columns(2)
        if c1.button("Update ✅", key="update_btn"):
            dur = hitung_durasi(new_masuk, new_keluar)
            try:
                row_idx = int(ed['row'])
                sheet.update(f"E{row_idx}:J{row_idx}", 
                             [[new_masuk, new_keluar, dur, new_uraian, new_output, ed.get("Lokasi","")]])
                st.sidebar.success("Berhasil!")
                del st.session_state.edit
                st.rerun()
            except Exception as e: st.sidebar.error(f"Gagal: {e}")
        
        if c2.button("Batal ❌", key="batal_btn"):
            del st.session_state.edit
            st.rerun()

# ================= DASHBOARD =================
if menu == "Dashboard":
    st.markdown(f"<div style='background:linear-gradient(90deg,#ef4444,#f87171);padding:20px;border-radius:12px;color:white;margin-bottom:20px;'><h2>📊 Aplikasi E-Kinerja</h2><p>{st.session_state.nama}</p></div>", unsafe_allow_html=True)
    df = load_data()
    if not df.empty:
        df["Durasi"] = df.apply(lambda r: hitung_durasi(r["Jam Masuk"], r["Jam Keluar"]), axis=1)
        df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')
        tgl = st.date_input("Range Tanggal", value=(df["Tanggal"].min(), df["Tanggal"].max()))
        if len(tgl)==2:
            df = df[(df["Tanggal"]>=pd.to_datetime(tgl[0])) & (df["Tanggal"]<=pd.to_datetime(tgl[1]))]
        
        c1,c2,c3,c4 = st.columns(4)
        c1.markdown(f"<div class='card c1'><h3>{len(df)}</h3>Total</div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='card c2'><h3>{df['Durasi'].sum():.2f}</h3>Jam</div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='card c3'><h3>{df['Tanggal'].nunique()}</h3>Hari</div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='card c4'><h3>{df['Nama'].nunique()}</h3>Pegawai</div>", unsafe_allow_html=True)
        st.bar_chart(df.groupby("Nama")["Durasi"].sum())

# ================= INPUT =================
elif menu == "Input":
    st.subheader("📍 Input Kinerja")
    lokasi = st.selectbox("Lokasi", ["Kantor", "Rumah", "Dinas Luar / SPT"])
    foto = None
    koordinat = ""

    if lokasi == "Rumah":
        foto = st.camera_input("Ambil Foto")
        from streamlit_js_eval import get_geolocation
        loc = get_geolocation()
        if loc:
            koordinat = f"{loc['coords']['latitude']}, {loc['coords']['longitude']}"
            st.success(f"GPS: {koordinat}")
    
    tgl = st.date_input("Tanggal")
    masuk = st.text_input("Jam Masuk", "07:30")
    keluar = st.text_input("Jam Keluar", "16:00")
    uraian = st.text_area("Uraian Kegiatan")
    output = st.text_area("Output/Hasil")

    if st.button("Simpan Data", type="primary"):
        dur = hitung_durasi(masuk, keluar)
        if not uraian or not output: st.error("Lengkapi data!")
        else:
            link_foto = upload_foto(foto) if lokasi == "Rumah" else ""
            sheet.append_row([st.session_state.nama, st.session_state.nip, st.session_state.jabatan, tgl.strftime("%Y-%m-%d"), masuk, keluar, dur, uraian, output, lokasi, koordinat, link_foto])
            st.success("Berhasil disimpan!")
            import time
            time.sleep(1)
            st.rerun()

# ================= DATA KINERJA =================
elif menu == "Data Kinerja":
    df = load_data()
    if df.empty: st.info("Belum ada data"); st.stop()
    
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')
    if st.session_state.role not in ["admin","pimpinan"]:
        df = df[df["NIP"].astype(str)==st.session_state.nip]

    for i, row in df.iterrows():
        with st.container():
            c1, c2, c3, c4 = st.columns([5,2,1,1])
            c1.write(f"**{row['Nama']}** - {row['Tanggal'].date()}")
            c1.caption(row["Uraian"])
            if row.get("Output"): c1.markdown(f"**Output:** {row['Output']}")
            
            # Tampilkan Foto
            if row.get("Foto") and str(row["Foto"]).startswith("data:image"):
                c1.image(row["Foto"], width=200)
            
            c2.write(f"{row['Durasi']} jam")
            if c3.button("✏️", key=f"edit{i}"):
                st.session_state.edit = row
                st.rerun()
            if c4.button("🗑", key=f"del{i}"):
                sheet.delete_rows(int(row["row"]))
                st.rerun()
            st.divider()

# ================= ADMIN =================
elif menu == "Admin":
    if st.session_state.role != "admin": st.error("Akses ditolak"); st.stop()
    # ... (Bagian Admin tetap seperti semula)
    nip_a = st.text_input("NIP Baru")
    nama_a = st.text_input("Nama Baru")
    if st.button("Tambah User"):
        user_sheet.append_row([nip_a, nama_a, "-", "123", "pegawai"])
        st.success("User ditambahkan")