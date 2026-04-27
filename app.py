import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import io
import plotly.express as px

# DRIVE
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ================= CONFIG =================
st.set_page_config(page_title="E-Kinerja KPU Kota Bengkulu", layout="wide")

# ================= SESSION DEFAULT =================
if "gps" not in st.session_state:
    st.session_state.gps = ""

if "foto" not in st.session_state:
    st.session_state.foto = None

# ================= STYLE =================
st.markdown("""
<style>
[data-testid="stSidebar"] {background:#0f172a;}
[data-testid="stSidebar"] * {color:white !important;}
.stButton button {background:#ef4444;color:white;border-radius:10px;}

.card {padding:18px;border-radius:14px;color:white;text-align:center;}
.c1{background:#ef4444;} .c2{background:#22c55e;}
.c3{background:#f59e0b;} .c4{background:#3b82f6;}

.header {
    background:linear-gradient(90deg,#ef4444,#f87171);
    padding:25px;border-radius:15px;color:white;margin-bottom:20px;
}
</style>
""", unsafe_allow_html=True)

# ================= GOOGLE =================
@st.cache_resource
def connect():
    creds = Credentials.from_service_account_info(
        st.secrets["connections"]["gsheets"]["service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ],
    )
    return gspread.authorize(creds).open_by_key(
        st.secrets["SPREADSHEET_ID"]
    )

@st.cache_resource
def connect_drive():
    creds = Credentials.from_service_account_info(
        st.secrets["connections"]["gsheets"]["service_account"],
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)

def upload_to_drive(file):
    service = connect_drive()

    file_bytes = io.BytesIO(file.getvalue())
    media = MediaIoBaseUpload(file_bytes, mimetype=file.type)

    file_metadata = {
        "name": f"foto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
        "parents": [st.secrets["DRIVE_FOLDER_ID"]]
    }

    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    file_id = uploaded.get("id")

    service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"}
    ).execute()

    return f"https://drive.google.com/file/d/{file_id}/view"

spreadsheet = connect()
sheet = spreadsheet.sheet1

# USERS
try:
    user_sheet = spreadsheet.worksheet("users")
except:
    user_sheet = spreadsheet.add_worksheet("users", 100, 5)
    user_sheet.append_row(["NIP","Nama","Jabatan","Password","Role"])

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
st.sidebar.caption(f"Role: {st.session_state.role.upper()}")

menu = st.sidebar.radio("Menu", ["Dashboard","Input","Data Kinerja","Admin"])

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ================= DASHBOARD =================
if menu == "Dashboard":

    st.markdown(f"""
    <div class='header'>
        <h2>Aplikasi E-Kinerja</h2>
        <p>{st.session_state.nama} - KPU Kota Bengkulu</p>
    </div>
    """, unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.info("Belum ada data")
        st.stop()

    df["Durasi"] = df.apply(lambda r: hitung_durasi(r["Jam Masuk"], r["Jam Keluar"]), axis=1)
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')

    # KPI
    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='card c1'><h2>{len(df)}</h2>Total</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card c2'><h2>{df['Durasi'].sum():.2f}</h2>Jam</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card c3'><h2>{df['Tanggal'].nunique()}</h2>Hari</div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card c4'><h2>{df['Nama'].nunique()}</h2>Pegawai</div>", unsafe_allow_html=True)

    chart = df.groupby("Nama")["Durasi"].sum().reset_index()
    fig = px.bar(chart, x="Nama", y="Durasi", color="Durasi", text_auto=True)
    st.plotly_chart(fig, use_container_width=True)

    # MAP
    if "GPS" in df.columns:
        st.markdown("### 📍 Peta Lokasi")
        df_map = df[df["GPS"] != ""]
        if not df_map.empty:
            df_map[["lat","lon"]] = df_map["GPS"].str.split(",", expand=True)
            df_map["lat"] = pd.to_numeric(df_map["lat"], errors="coerce")
            df_map["lon"] = pd.to_numeric(df_map["lon"], errors="coerce")
            st.map(df_map[["lat","lon"]])

# ================= INPUT =================
elif menu == "Input":

    st.subheader("Input Kinerja")

    tgl = st.date_input("Tanggal")
    masuk = st.text_input("Jam Masuk","07:30")
    keluar = st.text_input("Jam Keluar","16:00")
    uraian = st.text_area("Uraian")
    output = st.text_area("Output")

    lokasi = st.selectbox("Lokasi", ["Kantor","Rumah","Dinas Luar / SPT"])

    # ===== GPS + FOTO KHUSUS RUMAH =====
if lokasi == "Rumah":

    st.markdown("### 📡 GPS Otomatis")

    if "gps" not in st.session_state:
        st.session_state.gps = ""

    if st.button("📍 Ambil Lokasi GPS"):

        st.components.v1.html(f"""
        <script>
        navigator.geolocation.getCurrentPosition(
            function(pos) {{
                const coords = pos.coords.latitude + "," + pos.coords.longitude;

                // Cari input berdasarkan label
                const inputs = window.parent.document.querySelectorAll('input');

                inputs.forEach(input => {{
                    if(input.placeholder === "Koordinat GPS") {{
                        input.value = coords;
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }});

                alert("GPS berhasil: " + coords);
            }},
            function(err) {{
                alert("Gagal ambil GPS: " + err.message);
            }}
        );
        </script>
        """, height=0)

    gps = st.text_input(
        "Koordinat GPS",
        value=st.session_state.gps,
        placeholder="Koordinat GPS"
    )

    if gps:
        st.session_state.gps = gps

        st.markdown("### 📸 Ambil Foto")
        foto = st.camera_input("Foto Pegawai")
        if foto:
            st.session_state.foto = foto

    if st.button("💾 Simpan"):

        dur = hitung_durasi(masuk, keluar)

        if dur == 0:
            st.error("Jam tidak valid")
            st.stop()

        link_foto = ""

        if lokasi == "Rumah":

            if not st.session_state.gps:
                st.error("GPS wajib")
                st.stop()

            if not st.session_state.foto:
                st.error("Foto wajib")
                st.stop()

            link_foto = upload_to_drive(st.session_state.foto)

        sheet.append_row([
            safe(st.session_state.nama),
            safe(st.session_state.nip),
            safe(st.session_state.jabatan),
            safe(tgl.strftime("%Y-%m-%d")),
            safe(masuk),
            safe(keluar),
            dur,
            safe(uraian),
            safe(output),
            safe(lokasi),
            safe(st.session_state.gps),
            safe(link_foto)
        ])

        st.success("Data tersimpan")

        st.session_state.gps = ""
        st.session_state.foto = None

# ================= DATA =================
elif menu == "Data Kinerja":

    df = load_data()
    if df.empty:
        st.info("Belum ada data")
        st.stop()

    df["Durasi"] = df.apply(lambda r: hitung_durasi(r["Jam Masuk"], r["Jam Keluar"]), axis=1)

    for i,row in df.iterrows():
        st.write(f"{row['Nama']} - {row['Tanggal']} ({row['Durasi']} jam)")

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