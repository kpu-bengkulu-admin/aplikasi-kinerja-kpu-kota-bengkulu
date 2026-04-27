import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import io
import plotly.express as px
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ================= CONFIG =================
st.set_page_config(page_title="E-Kinerja KPU Kota Bengkulu", layout="wide")

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
    return gspread.authorize(creds).open_by_key("16l6pcqA1CvM-8P5rsT37UkMJnrEWTJW1CcOcS92WnlM")

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

# ================= DRIVE =================
FOLDER_ID = "1XRppl-J-WLoy0FM38au_ypPmg7faH1T9"

def upload_foto(file):
    creds = Credentials.from_service_account_info(
        st.secrets["connections"]["gsheets"]["service_account"]
    )
    service = build("drive", "v3", credentials=creds)

    file_metadata = {
        "name": f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.name}",
        "parents": [FOLDER_ID]
    }

    media = MediaIoBaseUpload(file, mimetype=file.type)

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

    return f"https://drive.google.com/uc?id={file_id}"

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login=False

if "gps" not in st.session_state:
    st.session_state.gps = ""

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

    col1,col2,col3 = st.columns(3)

    with col1:
        tgl = st.date_input("Range Tanggal", value=(df["Tanggal"].min(), df["Tanggal"].max()))

    with col2:
        pegawai = st.multiselect("Pegawai", sorted(df["Nama"].unique()))

    with col3:
        lokasi = st.multiselect("Lokasi", sorted(df["Lokasi"].unique()))

    if len(tgl)==2:
        df = df[(df["Tanggal"]>=pd.to_datetime(tgl[0])) & (df["Tanggal"]<=pd.to_datetime(tgl[1]))]

    if pegawai:
        df = df[df["Nama"].isin(pegawai)]

    if lokasi:
        df = df[df["Lokasi"].isin(lokasi)]

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='card c1'><h2>{len(df)}</h2>Total</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card c2'><h2>{df['Durasi'].sum():.2f}</h2>Jam</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card c3'><h2>{df['Tanggal'].nunique()}</h2>Hari</div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='card c4'><h2>{df['Nama'].nunique()}</h2>Pegawai</div>", unsafe_allow_html=True)

    # BAR CHART
    chart = df.groupby("Nama")["Durasi"].sum().reset_index()
    fig = px.bar(chart, x="Nama", y="Durasi", color="Durasi", text_auto=True)
    st.plotly_chart(fig, use_container_width=True)

    # MAP
    if "Koordinat" in df.columns:
        coords = df["Koordinat"].dropna()
        lat, lon = [], []

        for c in coords:
            try:
                a,b = c.split(",")
                lat.append(float(a))
                lon.append(float(b))
            except:
                pass

        if lat:
            map_df = pd.DataFrame({"lat":lat,"lon":lon})
            st.map(map_df)

# ================= INPUT =================
elif menu == "Input":

    st.subheader("📍 Input Kinerja")

    lokasi = st.selectbox("Lokasi", ["Kantor","Rumah","Dinas Luar / SPT"])

    gps = ""
    foto = None

    # ================= KHUSUS RUMAH =================
    if lokasi == "Rumah":

        st.markdown("### 📡 GPS Otomatis")

        if st.button("📍 Ambil Lokasi Sekarang"):

            st.components.v1.html("""
            <script>
            navigator.geolocation.getCurrentPosition(
                function(pos){
                    const coords = pos.coords.latitude + "," + pos.coords.longitude;

                    const inputs = window.parent.document.querySelectorAll('input');
                    inputs.forEach(i=>{
                        if(i.placeholder==="Koordinat GPS"){
                            i.value = coords;
                            i.dispatchEvent(new Event('input',{bubbles:true}));
                        }
                    });

                    alert("GPS: " + coords);
                },
                function(err){
                    alert("Gagal GPS: " + err.message);
                }
            );
            </script>
            """, height=0)

        gps = st.text_input(
            "Koordinat GPS",
            placeholder="Koordinat GPS"
        )

        st.markdown("### 📸 Ambil Foto (Kamera Langsung)")
        foto = st.camera_input("Ambil Foto Kehadiran")

    # ================= FORM =================
    with st.form("form"):

        tgl = st.date_input("Tanggal")
        masuk = st.text_input("Jam Masuk","07:30")
        keluar = st.text_input("Jam Keluar","16:00")
        uraian = st.text_area("Uraian")
        output = st.text_area("Output")

        submit = st.form_submit_button("💾 Simpan")

    # ================= SIMPAN =================
    if submit:

        dur = hitung_durasi(masuk, keluar)

        if dur == 0:
            st.error("Jam tidak valid")
            st.stop()

        # VALIDASI RUMAH
        if lokasi == "Rumah":

            if not gps:
                st.error("GPS wajib")
                st.stop()

            if foto is None:
                st.error("Foto wajib")
                st.stop()

            link_foto = upload_foto(foto)

        else:
            link_foto = ""

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
            safe(gps),
            safe(link_foto)
        ])

        st.success("✅ Data berhasil disimpan")

# ================= DATA =================
elif menu == "Data Kinerja":

    df = load_data()
    if df.empty:
        st.info("Belum ada data")
        st.stop()

    df["Durasi"] = df.apply(lambda r: hitung_durasi(r["Jam Masuk"], r["Jam Keluar"]), axis=1)
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')

    for i,row in df.iterrows():
        c1,c2,c3,c4 = st.columns([5,2,1,1])

        c1.write(f"**{row['Nama']}** - {row['Tanggal'].date()}")
        c2.write(f"{row['Durasi']:.2f} jam")

        if c3.button("✏️", key=f"edit{i}"):
            st.session_state.edit = row

        if c4.button("🗑", key=f"del{i}"):
            sheet.delete_rows(int(row["row"]))
            st.rerun()

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