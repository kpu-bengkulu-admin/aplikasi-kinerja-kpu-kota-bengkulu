import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import io
import plotly.express as px

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
.header {background:linear-gradient(90deg,#ef4444,#f87171);
padding:25px;border-radius:15px;color:white;margin-bottom:20px;}
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

    tgl = st.date_input("Range Tanggal", value=(df["Tanggal"].min(), df["Tanggal"].max()))
    pegawai = st.multiselect("Pegawai", sorted(df["Nama"].unique()))
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

    chart = df.groupby("Nama")["Durasi"].sum().reset_index()
    fig = px.bar(chart, x="Nama", y="Durasi", color="Durasi", text_auto=True)
    st.plotly_chart(fig, use_container_width=True)

    if "Lat" in df.columns and "Lon" in df.columns:
        map_df = df.dropna(subset=["Lat","Lon"])
        if not map_df.empty:
            map_df["Lat"] = pd.to_numeric(map_df["Lat"], errors='coerce')
            map_df["Lon"] = pd.to_numeric(map_df["Lon"], errors='coerce')
            st.map(map_df.rename(columns={"Lat":"lat","Lon":"lon"}))

# ================= INPUT =================
elif menu == "Input":

    st.subheader("Input Data")

    with st.form("form"):
        tgl = st.date_input("Tanggal")
        masuk = st.text_input("Jam Masuk","07:30")
        keluar = st.text_input("Jam Keluar","16:00")
        uraian = st.text_area("Uraian")
        output = st.text_area("Output")
        lokasi = st.selectbox("Lokasi", ["Kantor","Rumah","Dinas Luar / SPT"])
        foto = st.camera_input("Foto (wajib jika Rumah)") if lokasi=="Rumah" else None
        submit = st.form_submit_button("Simpan")

    # GPS DI LUAR FORM
    lat, lon = "", ""

    if lokasi == "Rumah":
        st.subheader("📍 Ambil Lokasi")

        if st.button("Ambil Lokasi"):
            st.session_state.get_loc = True

        koordinat = st.text_input("Koordinat", key="gps")

        if st.session_state.get("get_loc"):
            st.components.v1.html("""
            <script>
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    const coords = pos.coords.latitude + "," + pos.coords.longitude;
                    const inputs = window.parent.document.querySelectorAll('input');
                    inputs.forEach(i=>{
                        if(i.placeholder==="Koordinat"){
                            i.value=coords;
                            i.dispatchEvent(new Event('input',{bubbles:true}));
                        }
                    });
                }
            );
            </script>
            """, height=0)

        if koordinat and "," in koordinat:
            lat, lon = koordinat.split(",")

    if submit:
        dur = hitung_durasi(masuk, keluar)

        if dur == 0:
            st.error("Jam tidak valid")
            st.stop()

        if lokasi == "Rumah":
            if foto is None:
                st.error("Foto wajib")
                st.stop()
            if lat == "" or lon == "":
                st.error("Lokasi belum diambil")
                st.stop()

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
            safe(lat),
            safe(lon)
        ])

        st.success("Data tersimpan")
        st.session_state.get_loc=False

# ================= DATA =================
elif menu == "Data Kinerja":

    df = load_data()
    df["Durasi"] = df.apply(lambda r: hitung_durasi(r["Jam Masuk"], r["Jam Keluar"]), axis=1)
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')

    if st.session_state.role in ["admin","pimpinan"]:
        mode = st.radio("Mode Data", ["Semua Data","Data Saya"])
        if mode=="Data Saya":
            df = df[df["NIP"].astype(str)==st.session_state.nip]
    else:
        df = df[df["NIP"].astype(str)==st.session_state.nip]

    for i,row in df.iterrows():
        c1,c2,c3,c4 = st.columns([5,2,1,1])
        c1.write(f"**{row['Nama']}** - {row['Tanggal'].date()}")
        c2.write(f"{row['Durasi']} jam")

        if c3.button("✏️", key=f"e{i}"):
            st.session_state.edit=row

        if c4.button("🗑", key=f"d{i}"):
            sheet.delete_rows(int(row["row"]))
            st.rerun()

    if "edit" in st.session_state:
        ed = st.session_state.edit
        masuk = st.text_input("Masuk", ed["Jam Masuk"])
        keluar = st.text_input("Keluar", ed["Jam Keluar"])

        if st.button("Update"):
            row_num=int(ed["row"])
            dur=hitung_durasi(masuk,keluar)

            sheet.update(f"E{row_num}", masuk)
            sheet.update(f"F{row_num}", keluar)
            sheet.update(f"G{row_num}", dur)

            st.success("Updated")
            del st.session_state.edit
            st.rerun()

# ================= ADMIN =================
elif menu == "Admin":

    if st.session_state.role!="admin":
        st.error("Akses ditolak")
        st.stop()

    nip=st.text_input("NIP")
    nama=st.text_input("Nama")
    jab=st.text_input("Jabatan")
    pw=st.text_input("Password")
    role=st.selectbox("Role",["pegawai","admin","pimpinan"])

    if st.button("Tambah User"):
        user_sheet.append_row([nip,nama,jab,pw,role])
        st.success("User ditambahkan")