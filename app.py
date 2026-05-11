import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import io

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ================= SESSION =================
if "gps" not in st.session_state:
    st.session_state.gps = ""

# ================= DRIVE =================
FOLDER_ID = "1XRppl-J-WLoy0FM38au_ypPmg7faH1T9"

def upload_foto(file):
    # (Bagian info dan creds tetap sama seperti sebelumnya)
    info = { ... } 
    creds = Credentials.from_service_account_info(info)
    service = build("drive", "v3", credentials=creds)

    file.seek(0) 

    file_metadata = {
        "name": file.name,
        "parents": [FOLDER_ID] 
    }

    media = MediaIoBaseUpload(file, mimetype=file.type, resumable=True)

    try:
        # Tambahkan supportsAllDrives=True untuk mengatasi masalah kuota
        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True
        ).execute()

        file_id = uploaded.get("id")

        # Beri izin akses publik (opsional)
        service.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "anyone"}
        ).execute()

        return f"https://drive.google.com/uc?id={file_id}"
    
    except Exception as e:
        st.error(f"Gagal upload: {e}")
        return ""


# ================= CONFIG =================
st.set_page_config(
    page_title="E-Kinerja KPU Kota Bengkulu",
    page_icon="📊",
    layout="wide"
)

# ================= UI =================
st.markdown("""
<style>
[data-testid="stSidebar"] {background:#0f172a;}
[data-testid="stSidebar"] * {color:white !important;}
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

# Inisialisasi Spreadsheet dan Sheet
spreadsheet = connect()
sheet = spreadsheet.sheet1

# DEFINISIKAN user_sheet DI SINI SEBELUM DIPANGGIL
try:
    user_sheet = spreadsheet.worksheet("users")
except gspread.exceptions.WorksheetNotFound:
    # Jika sheet "users" tidak ada, buat baru
    user_sheet = spreadsheet.add_worksheet("users", 100, 5)
    user_sheet.append_row(["NIP", "Nama", "Jabatan", "Password", "Role"])
except Exception as e:
    st.error(f"Gagal mengakses sheet users: {e}")
    st.stop()

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
    except:
        return None

def hitung_durasi(masuk, keluar):
    jm = parse_jam(masuk)
    jk = parse_jam(keluar)
    if jm and jk and jk > jm:
        return round((jk-jm)/60,2)
    return 0

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login=False

users = load_users()

if not st.session_state.login:
    st.title("🔐 Login E-Kinerja KPU Kota Bengkulu")

    nip = st.text_input("NIP")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):
        cek = users[
            (users["NIP"].astype(str)==str(nip)) &
            (users["Password"].astype(str)==str(pw))
        ]
        if not cek.empty:
            u = cek.iloc[0]
            st.session_state.login=True
            st.session_state.nama=u["Nama"]
            st.session_state.nip=str(u["NIP"])
            st.session_state.jabatan=u["Jabatan"]
            st.session_state.role=u["Role"]
            st.rerun()
        else:
            st.error("Login gagal")
    st.stop()

# ================= SIDEBAR =================
st.sidebar.title(st.session_state.nama)
menu = st.sidebar.radio("Menu", ["Dashboard","Input","Data Kinerja","Admin"])

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ================= DASHBOARD =================
if menu == "Dashboard":

    st.markdown(f"""
    <div style="
        background:linear-gradient(90deg,#ef4444,#f87171);
        padding:20px;
        border-radius:12px;
        color:white;
        margin-bottom:20px;
    ">
        <h2>📊 Aplikasi E-Kinerja</h2>
        <p>{st.session_state.nama} - KPU Kota Bengkulu</p>
    </div>
    """, unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.info("Belum ada data")
        st.stop()

    df["Durasi"] = df.apply(lambda r: hitung_durasi(r["Jam Masuk"], r["Jam Keluar"]), axis=1)
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')

    # RANGE OTOMATIS (FIX)
    start_default = df["Tanggal"].min()
    end_default = df["Tanggal"].max()

    tgl = st.date_input("Range Tanggal", value=(start_default, end_default))

    if len(tgl)==2:
        df = df[(df["Tanggal"]>=pd.to_datetime(tgl[0])) & (df["Tanggal"]<=pd.to_datetime(tgl[1]))]

    pegawai = st.multiselect("Pegawai", sorted(df["Nama"].unique()))
    lokasi = st.multiselect("Lokasi", sorted(df["Lokasi"].unique()))

    if pegawai:
        df = df[df["Nama"].isin(pegawai)]
    if lokasi:
        df = df[df["Lokasi"].isin(lokasi)]

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='card c1'><h3>{len(df)}</h3>Total</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card c2'><h3>{df['Durasi'].sum():.2f}</h3>Jam</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card c3'><h3>{df['Tanggal'].nunique()}</h3>Hari</div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card c4'><h3>{df['Nama'].nunique()}</h3>Pegawai</div>", unsafe_allow_html=True)

    st.bar_chart(df.groupby("Nama")["Durasi"].sum())

# ================= INPUT =================
elif menu == "Input":
    st.subheader("📍 Input Kinerja")
    
    # 1. Pilih Lokasi
    lokasi = st.selectbox("Lokasi", ["Kantor", "Rumah", "Dinas Luar / SPT"])
    
    foto = None
    koordinat = ""

    # 2. KHUSUS RUMAH (Hanya muncul jika pilih Rumah)
    if lokasi == "Rumah":
        st.markdown("### 📸 Verifikasi WFH")
        foto = st.camera_input("Ambil Foto Langsung")
        
        from streamlit_js_eval import get_geolocation
        loc = get_geolocation()
        if loc:
            koordinat = f"{loc['coords']['latitude']}, {loc['coords']['longitude']}"
            st.success(f"✅ GPS Terdeteksi: {koordinat}")
        else:
            st.warning("📡 Menunggu GPS... Pastikan klik 'Allow' di browser.")
        
        st.text_input("Koordinat GPS (Otomatis)", value=koordinat, disabled=True)
        st.divider()

    # 3. ISIAN DETAIL LAPORAN (Muncul untuk semua lokasi)
    tgl = st.date_input("Tanggal")
    masuk = st.text_input("Jam Masuk", "07:30")
    keluar = st.text_input("Jam Keluar", "16:00")
    uraian = st.text_area("Uraian Kegiatan")
    output = st.text_input("Output/Hasil")

    # 4. TOMBOL SIMPAN (Hanya Satu)
    if st.button("Simpan Data", type="primary"):
        # Hitung durasi (Menggunakan fungsi Anda)
        dur = hitung_durasi(masuk, keluar)

        # VALIDASI
        if not uraian or not output:
            st.error("⚠️ Uraian dan Output wajib diisi!")
        elif dur == 0:
            st.error("⚠️ Jam tidak valid!")
        elif lokasi == "Rumah" and (foto is None or koordinat == ""):
            st.error("⚠️ Untuk Rumah, Foto dan GPS wajib ada!")
        else:
            # PROSES FOTO (Jika Rumah)
            link_foto = ""
            if lokasi == "Rumah":
                link_foto = upload_foto(foto) # Menggunakan fungsi Anda

            # PROSES SIMPAN KE GOOGLE SHEETS
            sheet.append_row([
                safe(st.session_state.nama),
                safe(str(st.session_state.nip)),
                safe(st.session_state.jabatan),
                safe(tgl.strftime("%Y-%m-%d")),
                safe(masuk),
                safe(keluar),
                dur,
                safe(uraian),
                safe(output),
                safe(lokasi),
                safe(koordinat),
                safe(link_foto)
            ])

            st.success(f"🎉 Data Kinerja ({lokasi}) Berhasil Disimpan!")
            
            # Reset state dan Refresh
            st.session_state.gps = ""
            import time
            time.sleep(2)
            st.rerun()

# ================= DATA =================
elif menu == "Data Kinerja":

    df = load_data()
    if df.empty:
        st.info("Belum ada data")
        st.stop()

    df["Durasi"] = df.apply(lambda r: hitung_durasi(r["Jam Masuk"], r["Jam Keluar"]), axis=1)
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')

    # FILTER ROLE
    if st.session_state.role in ["admin","pimpinan"]:
        mode = st.radio("Mode Data", ["Semua Data","Data Saya"])
        if mode == "Data Saya":
            df = df[df["NIP"].astype(str)==st.session_state.nip]
    else:
        df = df[df["NIP"].astype(str)==st.session_state.nip]

    # FILTER TANGGAL
    tgl = st.date_input("Filter Tanggal", value=(df["Tanggal"].min(), df["Tanggal"].max()))

    if len(tgl)==2:
        df = df[(df["Tanggal"]>=pd.to_datetime(tgl[0])) & (df["Tanggal"]<=pd.to_datetime(tgl[1]))]

    # TAMPIL DATA
    for i,row in df.iterrows():

        c1,c2,c3,c4 = st.columns([5,2,1,1])

        c1.write(f"**{row['Nama']}** - {row['Tanggal'].date()}")
        c1.caption(row["Uraian"])

        if "Koordinat" in row and row["Koordinat"]:
            c1.write(f"📍 {row['Koordinat']}")

        if "Foto" in row and row["Foto"]:
            c1.markdown(f"[📸 Lihat Foto]({row['Foto']})")

        c2.write(f"{row['Durasi']:.2f} jam")

        if c3.button("✏️", key=f"edit{i}"):
            st.session_state.edit = row

        if c4.button("🗑", key=f"del{i}"):
            sheet.delete_rows(int(row["row"]))
            st.rerun()

    # EDIT
    if "edit" in st.session_state:
        ed = st.session_state.edit

        st.subheader("✏️ Edit Data")

        masuk = st.text_input("Jam Masuk", ed["Jam Masuk"])
        keluar = st.text_input("Jam Keluar", ed["Jam Keluar"])
        uraian = st.text_area("Uraian", ed["Uraian"])
        output = st.text_area("Output", ed["Output"])

        if st.button("Update"):
            dur = hitung_durasi(masuk, keluar)

            sheet.update(
                f"E{int(ed['row'])}:J{int(ed['row'])}",
                [[masuk, keluar, dur, uraian, output, ed["Lokasi"]]]
            )

            del st.session_state.edit
            st.success("Update berhasil")
            st.rerun()

    # DOWNLOAD
    st.divider()

    excel = io.BytesIO()
    df.to_excel(excel, index=False)

    st.download_button(
        "📥 Download Excel",
        excel.getvalue(),
        file_name="data_kinerja.xlsx"
    )

# ================= ADMIN =================
elif menu == "Admin":

    if st.session_state.role != "admin":
        st.error("Akses ditolak")
        st.stop()

    nip = st.text_input("NIP")
    nama = st.text_input("Nama")
    jab = st.text_input("Jabatan")
    pw = st.text_input("Password")
    role = st.selectbox("Role", ["pegawai","admin","pimpinan"])

    if st.button("Tambah User"):
        user_sheet.append_row([nip,nama,jab,pw,role])
        st.success("User ditambahkan")