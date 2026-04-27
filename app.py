import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import plotly.express as px

# ================= CONFIG =================
st.set_page_config(page_title="E-Kinerja KPU Kota Bengkulu", layout="wide")

# ================= SESSION =================
if "gps" not in st.session_state:
    st.session_state.gps = ""

# ================= GOOGLE =================
@st.cache_resource
def connect_sheet():
    creds = Credentials.from_service_account_info(
        st.secrets["connections"]["gsheets"]["service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ],
    )
    return gspread.authorize(creds).open_by_key(st.secrets["SPREADSHEET_ID"])

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

    file_upload = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    file_id = file_upload.get("id")

    return f"https://drive.google.com/file/d/{file_id}/view"

# ================= CONNECT =================
spreadsheet = connect_sheet()
sheet = spreadsheet.sheet1

# ================= HELPER =================
def safe(x): return "" if x is None else str(x)

def load_data():
    df = pd.DataFrame(sheet.get_all_records())
    if not df.empty:
        df["row"] = range(2, len(df)+2)
    return df

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
    st.session_state.login = False

if not st.session_state.login:

    st.title("🔐 Login E-Kinerja")

    nip = st.text_input("NIP")
    pw = st.text_input("Password", type="password")

    if st.button("Login"):
        users = pd.DataFrame(spreadsheet.worksheet("users").get_all_records())

        cek = users[
            (users["NIP"].astype(str)==str(nip)) &
            (users["Password"].astype(str)==str(pw))
        ]

        if not cek.empty:
            u = cek.iloc[0]
            st.session_state.login=True
            st.session_state.nama=u["Nama"]
            st.session_state.nip=str(u["NIP"])
            st.session_state.role=u["Role"]
            st.rerun()
        else:
            st.error("Login gagal")

    st.stop()

# ================= SIDEBAR =================
st.sidebar.title(st.session_state.nama)
menu = st.sidebar.radio("Menu", ["Dashboard","Input","Data"])

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ================= DASHBOARD =================
if menu == "Dashboard":

    st.title("📊 Dashboard")

    df = load_data()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    df["Durasi"] = df.apply(lambda r: hitung_durasi(r["Jam Masuk"], r["Jam Keluar"]), axis=1)

    # ===== MAP =====
    if "Koordinat" in df.columns:
        gps_df = df.dropna(subset=["Koordinat"])

        if not gps_df.empty:
            gps_df[["lat","lon"]] = gps_df["Koordinat"].str.split(",", expand=True).astype(float)
            st.map(gps_df)

    # ===== CHART =====
    chart = df.groupby("Nama")["Durasi"].sum().reset_index()
    fig = px.bar(chart, x="Nama", y="Durasi", color="Durasi", text_auto=True)
    st.plotly_chart(fig, use_container_width=True)

# ================= INPUT =================
elif menu == "Input":

    st.title("📍 Input Kinerja")

    lokasi = st.selectbox("Lokasi", ["Kantor","Rumah","Dinas Luar / SPT"])

    # ===== GPS =====
    if lokasi == "Rumah":

        st.subheader("📡 GPS Otomatis")

        if st.button("📍 Ambil GPS"):

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
                    alert("GPS: "+coords);
                },
                function(err){alert(err.message);}
            );
            </script>
            """, height=0)

    # ===== FORM =====
    with st.form("form"):

        tgl = st.date_input("Tanggal")
        masuk = st.text_input("Jam Masuk","07:30")
        keluar = st.text_input("Jam Keluar","16:00")
        uraian = st.text_area("Uraian")
        output = st.text_area("Output")

        gps = st.text_input(
            "Koordinat GPS",
            value=st.session_state.get("gps",""),
            placeholder="Koordinat GPS"
        )

        st.session_state.gps = gps

        foto = None
        if lokasi == "Rumah":
            foto = st.file_uploader("Upload Foto", type=["jpg","png","jpeg"])

        submit = st.form_submit_button("💾 Simpan")

    # ===== SIMPAN =====
    if submit:

        dur = hitung_durasi(masuk, keluar)

        if dur == 0:
            st.error("Jam tidak valid")
            st.stop()

        link_foto = ""

        if lokasi == "Rumah":

            if not st.session_state.gps:
                st.error("GPS wajib")
                st.stop()

            if foto is None:
                st.error("Foto wajib")
                st.stop()

            link_foto = upload_to_drive(foto)

        sheet.append_row([
            safe(st.session_state.nama),
            safe(st.session_state.nip),
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

        st.success("Data berhasil disimpan")
        st.session_state.gps = ""

# ================= DATA =================
elif menu == "Data":

    st.title("📄 Data Kinerja")

    df = load_data()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    st.dataframe(df, use_container_width=True)