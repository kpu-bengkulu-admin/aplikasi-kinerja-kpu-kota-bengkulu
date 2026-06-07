import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import gspread
from google.oauth2.service_account import Credentials
import io
import base64
import uuid

from PIL import Image

from openpyxl.styles import Alignment

# ================= CONFIG =================
st.set_page_config(
    page_title="E-Kinerja KPU KOTA BENGKULU",
    page_icon="logo_kpu.png",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.sidebar.empty()

st.markdown("""
<style>

/* Header transparan tapi tetap aktif */
header {
    background: transparent !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #0f172a !important;
    width: 260px !important;
}

/* GLOBAL CONTAINER */
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

[data-testid="stAppViewContainer"] {
    padding-top: 0rem !important;
}

/* Tombol sidebar JANGAN disembunyikan */
button[kind="header"] {
    display: block !important;
    opacity: 1 !important;
    visibility: visible !important;
}

/* Footer */
footer {
    visibility: hidden;
}

</style>
""", unsafe_allow_html=True)


from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ================= SESSION =================
if "gps" not in st.session_state:
    st.session_state.gps = ""

# ================= DRIVE =================
FOLDER_ID = "1c2dL7ojqrQPqt7SjYCeI7L_NBhRApped"

def upload_foto(file):
    if file is None: return ""
    
    try:
        # 1. Buka foto dan perkecil ukurannya (agar tidak membebani Spreadsheet)
        img = Image.open(file)
        img.thumbnail((300, 300))  
        
        # 2. Ubah foto menjadi teks (Base64)
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=70) # Kompres kualitas ke 70%
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # 3. Kita tidak upload ke Drive, tapi kirim teks ini kembali
        # Kita buat link tiruan yang isinya data foto
        return img_str

    except Exception as e:
        st.error(f"Gagal memproses foto: {e}")
        return ""

# ================= UI CUSTOM (SIDEBAR FIX) =================
st.markdown("""
<style>
/* 1. Latar belakang sidebar */
[data-testid="stSidebar"] {background:#0f172a !important;}

/* 2. PAKSA SEMUA TEKS DI SIDEBAR MENJADI PUTIH */
/* Ini akan menyasar semua jenis teks: label, radio button, markdown, dll */
[data-testid="stSidebar"] * {
    color: white !important;
}

/* 3. KHUSUS UNTUK MENU RADIO (DASHBOARD, INPUT, DLL) */
/* Terkadang label radio butuh penanganan ekstra agar tidak transparan */
div[data-testid="stSidebar"] .st-emotion-cache-6qob1r {
    color: white !important;
    opacity: 1 !important;
}

/* 4. KOTAK INPUT EDIT (Tetap Hitam agar terlihat di latar putih) */
/* Kita kecualikan agar teks yang kita ketik tetap hitam di kotak putih */
[data-testid="stSidebar"] input, 
[data-testid="stSidebar"] textarea {
    color: black !important;
    background-color: white !important;
    -webkit-text-fill-color: black !important;
}

/* 5. Tombol Logout agar tetap merah terang */
.stButton button {
    background-color: #ef4444 !important;
    color: white !important;
    border-radius: 10px !important;
    border: none !important;
}
/* PERBAIKI DROPDOWN */
[data-baseweb="select"] {
    background: white !important;
    border-radius: 10px !important;
}

[data-baseweb="select"] svg {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    fill: #0f172a !important;
    color: #0f172a !important;
}
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

# ================= SPREADSHEET =================
try:
    spreadsheet = connect()

    # Ganti "Sheet1" sesuai nama sheet utama Anda
    sheet = spreadsheet.worksheet("data_kinerja")

except Exception as e:
    st.error(f"Gagal koneksi Spreadsheet utama: {e}")
    st.stop()

# ================= USER SHEET =================
try:
    user_sheet = spreadsheet.worksheet("users")

except gspread.exceptions.WorksheetNotFound:

    # Jika sheet users belum ada
    user_sheet = spreadsheet.add_worksheet(
        title="users",
        rows=100,
        cols=5
    )

    user_sheet.append_row([
        "NIP",
        "Nama",
        "Jabatan",
        "Password",
        "Role"
    ])

except Exception as e:
    st.error(f"Gagal mengakses sheet users: {e}")
    st.stop()

# ================= HELPER =================
def safe(x): return "" if x is None else str(x)

@st.cache_data(ttl=300)
def load_users():

    data = user_sheet.get_values()

    if len(data) < 2:
        return pd.DataFrame()

    return pd.DataFrame(
        data[1:],
        columns=data[0]
    )

@st.cache_data(ttl=300)
def load_data():

    data = sheet.get_values()

    if len(data) < 2:
        return pd.DataFrame()

    df = pd.DataFrame(
        data[1:],
        columns=data[0]
    )

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

    if jm is None or jk is None:
        return 0

    # Shift malam lintas hari
    if jk < jm:
        jk += 24 * 60

    return round((jk - jm) / 60, 2)

@st.cache_data(ttl=30)
def load_config():

    try:

        config_sheet = spreadsheet.worksheet(
            "CONFIG"
        )

        data = config_sheet.get_all_records()

        return pd.DataFrame(data)

    except:

        return pd.DataFrame()

# ================= SESSION LOGIN =================
if "login" not in st.session_state:
    st.session_state.login = False

if "sukses_simpan" not in st.session_state:
    st.session_state.sukses_simpan = False

if "nama" not in st.session_state:
    st.session_state.nama = ""

if "nip" not in st.session_state:
    st.session_state.nip = ""

if "jabatan" not in st.session_state:
    st.session_state.jabatan = ""

if "role" not in st.session_state:
    st.session_state.role = ""

if "unit" not in st.session_state:
    st.session_state.unit = ""

if "show_toast" not in st.session_state:
    st.session_state.show_toast = False

try:
    users = load_users()
except Exception as e:
    st.error("⚠️ Google Sheets sedang sibuk. Coba beberapa saat lagi.")
    st.stop()

if not st.session_state.login:
    st.title("🔐 Login E-Kinerja KPU KOTA BENGKULU")

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
            st.session_state.unit = u["Unit"]
            st.rerun()
        else:
            st.error("Login gagal")
    st.stop()

# ================= MAINTENANCE =================

config = load_config()

maintenance = "OFF"

if not config.empty:

    row = config[
        config["Key"]
        .astype(str)
        .str.lower()
        == "maintenance"
    ]

    if not row.empty:

        maintenance = str(
            row.iloc[0]["Value"]
        ).upper()

if (
    maintenance == "ON"
    and st.session_state.role != "Admin"
):

    st.markdown("""
    <div style="
        text-align:center;
        padding-top:120px;
    ">
        <h1>🛠️ Maintenance</h1>

        <h3>
        Aplikasi E-Kinerja KPU Kota Bengkulu
        Sedang Dalam Pemeliharaan
        </h3>

        <p>
        Mohon maaf atas ketidaknyamanan ini.
        Silakan coba kembali beberapa saat lagi.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# ================= SIDEBAR =================
st.sidebar.image("logo_kpu.png", width=100)
st.sidebar.title(
    st.session_state.get("nama", "Guest")
)

st.sidebar.markdown(
    f"""
    <p style='margin-top:-10px; color:gray;'>
    {st.session_state.role}
    </p>

    <p style='margin-top:-10px; color:gray;'>
    {st.session_state.unit}
    </p>
    """,
    unsafe_allow_html=True
)

if st.session_state.show_toast:
    st.toast(
        "✅ Data berhasil disimpan",
        icon="👍"
    )
    st.session_state.show_toast = False

menu = st.sidebar.radio(
    "Menu",
    ["Dashboard", "Input", "Data Kinerja", "Admin"]
)

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
# --- BAGIAN EDIT (TAMBAHKAN DI SINI AGAR MUNCUL DI SIDEBAR) ---
if "edit" in st.session_state:
    ed = st.session_state.edit
    
    st.sidebar.divider()
    st.sidebar.subheader("✏️ Edit Data")
    st.sidebar.info(f"Mengedit data baris: {ed['row']}")

    # Gunakan kunci (key) unik agar Streamlit tidak bingung
    new_masuk = st.sidebar.text_input("Jam Masuk", ed["Jam Masuk"], key="edit_masuk")
    new_keluar = st.sidebar.text_input("Jam Keluar", ed["Jam Keluar"], key="edit_keluar")
    new_uraian = st.sidebar.text_area("Uraian", ed["Uraian"], key="edit_uraian", height=150)
    new_output = st.sidebar.text_area("Output", ed["Output"], key="edit_output", height=150)

    col1, col2 = st.sidebar.columns(2)
    
    if col1.button("Update ✅", key="update_final"):
        dur = hitung_durasi(new_masuk, new_keluar)
        # Update ke Google Sheets (Kolom E sampai J)
        try:
            row_idx = int(ed['row'])
            sheet.update(
                f"E{row_idx}:J{row_idx}",
                [[new_masuk, new_keluar, dur, new_uraian, new_output, ed["Lokasi"]]]
            )
            load_data.clear()

            st.sidebar.success("Data Berhasil Diperbarui!")
            del st.session_state.edit
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

    if col2.button("Batal ❌", key="btn_batal"):
        del st.session_state.edit
        st.rerun()

# ================= DASHBOARD =================
if menu == "Dashboard":

    # ================= CUSTOM CSS =================
    st.markdown("""
    <style>

    .stApp {
        background-color: #f1f5f9;
    }

/* HERO */
.hero {
    background: linear-gradient(135deg,#0f172a,#1e293b);
    padding: 10px 16px;
    border-radius: 12px;
    color: white;
    margin-bottom: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.10);
}

/* Judul hero */
.hero h1 {
    font-size: 30px !important;
    margin-bottom: 2px !important;
}

/* Subjudul */
.hero h4 {
    font-size: 15px !important;
    margin-bottom: 2px !important;
}

/* Text kecil */
.hero p {
    font-size: 12px !important;
    margin-bottom: 0px !important;
}

/* KPI CARD */
.kpi-card {
    background: white;
    padding: 12px;
    border-radius: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border-left: 4px solid #ef4444;
}

/* Judul KPI */
.kpi-title {
    font-size: 11px;
    color: gray;
}

/* Angka KPI */
.kpi-value {
    font-size: 22px;
    font-weight: bold;
    color: #0f172a;
}

/* Filter */
.filter-box {
    padding: 12px;
    border-radius: 14px;
    margin-bottom: 10px;
}

/* Grafik */
.js-plotly-plot {
    border-radius: 14px;
    overflow: hidden;
}

/* RESPONSIVE HP */
@media (max-width: 768px) {

    .hero {
        padding: 8px 12px;
        border-radius: 10px;
    }

    .hero h1 {
        font-size: 18px !important;
    }

    .hero h4 {
        font-size: 13px !important;
    }

    .hero p {
        font-size: 11px !important;
    }

    .kpi-card {
        padding: 10px;
        border-radius: 10px;
    }

    .kpi-title {
        font-size: 10px;
    }

    .kpi-value {
        font-size: 18px;
    }

    .filter-box {
        padding: 10px;
    }

    /* Rapatkan dashboard */
    .block-container {
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
    }
}

    .kpi-card:hover {
        transform: translateY(-5px);
    }

    .kpi-title {
        color: gray;
        font-size: 14px;
    }

    .kpi-value {
        font-size: 35px;
        font-weight: bold;
        color: #0f172a;
    }

    /* FILTER BOX */
    .filter-box {
        background: white;
        padding: 20px;
        border-radius: 20px;
        margin-bottom: 20px;
        box-shadow: 0 3px 8px rgba(0,0,0,0.06);
    }

    /* TABLE */
    .stDataFrame {
        border-radius: 15px;
        overflow: hidden;
    }

    </style>
    """, unsafe_allow_html=True)

    # ================= HERO =================
    st.markdown(f"""
    <div class="hero">
        <h1>📊 E-Kinerja KPU Kota Bengkulu</h1>
        <h4>Selamat Datang, {st.session_state.nama}</h4>
        <p style="opacity:0.8;">
        Sistem Monitoring & Evaluasi Kinerja Pegawai
        </p>
        <p>
            {datetime.now().strftime("%A, %d %B %Y")}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ================= LOAD DATA =================
    df = load_data()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    # ================= FORMAT DATA =================
    if "Durasi" in df.columns:

        df["Durasi"] = pd.to_numeric(
            df["Durasi"],
            errors="coerce"
        ).fillna(0)

    elif "Durasi" in df.columns:

        df["Durasi"] = (
            df["Durasi"]
            .astype(str)
            .str.strip()
            .str.replace(",", ".", regex=False)
        )

        df["Durasi"] = pd.to_numeric(
            df["Durasi"],
            errors="coerce"
        ).fillna(0)

        df["Durasi"] = df["Durasi"].astype(float)

    else:

        df["Durasi"] = df.apply(
            lambda r: hitung_durasi(
                r["Jam Masuk"],
                r["Jam Keluar"]
            ),
            axis=1
        )

    df["Tanggal"] = pd.to_datetime(
        df["Tanggal"],
        errors='coerce'
    )

    df = df.dropna(subset=["Tanggal"])

    # ================= ROLE =================

    if st.session_state.role == "Admin":

        pass

    elif st.session_state.role == "Pimpinan":

        pass

    elif st.session_state.role == "Kasubbag":

        df = df[
            df["Unit"]
            == st.session_state.unit
        ]

    else:

        df = df[
            df["NIP"].astype(str)
            == st.session_state.nip
        ]

    # ================= FILTER =================

    col1, col2, col3 = st.columns(
        3,
        gap="medium"
    )

    # ================= COL 1 =================
    with col1:

        today = date.today()

        if df.empty:
            start_default = today
            end_default = today

        else:

            if "Tanggal" not in df.columns:
                start_default = today
                end_default = today

            else:

                df["Tanggal"] = pd.to_datetime(
                    df["Tanggal"],
                    errors="coerce"
                )

                start_default = df["Tanggal"].min()
                end_default = df["Tanggal"].max()

                if pd.isna(start_default):
                    start_default = today
                else:
                    start_default = start_default.date()

                if pd.isna(end_default):
                    end_default = today
                else:
                    end_default = end_default.date()

        tgl = st.date_input(
            "📅 Range Tanggal",
            value=(start_default, end_default)
        )

    # ================= COL 2 =================
    with col2:

        Pegawai = st.multiselect(
            "👤 Pegawai",
            sorted(df["Nama"].unique())
        )

    # ================= COL 3 =================
    with col3:

        lokasi = st.multiselect(
            "📍 Lokasi",
            sorted(df["Lokasi"].unique())
        )


    # ================= FILTER PROSES =================
    if len(tgl) == 2:

        df = df[
            (df["Tanggal"] >= pd.to_datetime(tgl[0])) &
            (df["Tanggal"] <= pd.to_datetime(tgl[1]))
        ]

    if Pegawai:
        df = df[
            df["Nama"].isin(Pegawai)
        ]

    if lokasi:
        df = df[
            df["Lokasi"].isin(lokasi)
        ]

    # ================= KPI =================
    k1, k2, k3, k4 = st.columns(4)

    with k1:

        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">📄 Total Kinerja</div>
            <div class="kpi-value">{len(df)}</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:

        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">⏱ Total Jam</div>
            <div class="kpi-value">{df['Durasi'].sum():.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:

        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">📅 Hari Aktif</div>
            <div class="kpi-value">{df['Tanggal'].nunique()}</div>
        </div>
        """, unsafe_allow_html=True)

    with k4:

        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">👥 Pegawai</div>
            <div class="kpi-value">{df['Nama'].nunique()}</div>
        </div>
        """, unsafe_allow_html=True)

    # ================= GRAFIK =================
    g1, g2 = st.columns(2)

    with g1:

        chart1 = (
            df.groupby("Nama")["Durasi"]
            .sum()
            .reset_index()
        )

        fig = px.bar(
            chart1,
            x="Nama",
            y="Durasi",
            text_auto=True,
            title="📊 Produktivitas Pegawai"
        )

        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=300
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with g2:

        chart2 = (
            df.groupby("Lokasi")
            .size()
            .reset_index(name="Total")
        )

        fig2 = px.pie(
            chart2,
            names="Lokasi",
            values="Total",
            hole=0.5,
            title="📍 Distribusi Lokasi Kerja"
        )

        fig2.update_layout(
            height=300
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )

    # ================= RANKING =================
    if st.session_state.role in [
        "Admin",
        "Pimpinan",
        "Kasubbag"
    ]:

        st.markdown("## 🏆 Ranking Pegawai")

        ranking = (
            df.groupby("Nama")["Durasi"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )

        ranking.columns = [
            "Nama Pegawai",
            "Total Jam"
        ]

        ranking.index += 1

        st.dataframe(
            ranking,
            use_container_width=True
        )

    # ================= FOOTER =================
    st.markdown("""
    <hr>
    <center>
    © 2025 KPU Kota Bengkulu | Sistem E-Kinerja Digital
    </center>
    """, unsafe_allow_html=True)

# ================= INPUT =================
elif menu == "Input":

    st.subheader("📍 Input Kinerja")

    lokasi = st.selectbox(
        "Lokasi",
        ["Kantor", "Rumah", "Dinas Luar / SPT"]
    )

    foto = None
    koordinat = ""
    waktu_absen = "-"

    # ================= KHUSUS WFH =================
    if lokasi == "Rumah":

        waktu_absen = st.selectbox(
            "Waktu Absen",
            ["Pagi", "Siang", "Sore"]
        )

        st.markdown("### 📸 Verifikasi WFH")

        foto = st.camera_input(
            "Ambil Foto Langsung"
        )

        from streamlit_js_eval import get_geolocation

        loc = get_geolocation()

        if loc:

            koordinat = (
                f"{loc['coords']['latitude']}, "
                f"{loc['coords']['longitude']}"
            )

            st.success(
                f"✅ GPS Terdeteksi: {koordinat}"
            )

        else:

            st.warning(
                "📡 Menunggu GPS..."
            )

        st.text_input(
            "Koordinat GPS",
            value=koordinat,
            disabled=True
        )

        st.divider()

    # ================= FORM UTAMA =================
    # INI HARUS DI LUAR IF RUMAH

    # ================= RESET FORM =================
    if "form_id" not in st.session_state:
        st.session_state.form_id = 0

    form_key = str(st.session_state.form_id)

# ================= FORM INPUT =================
    # ================= FORM INPUT =================
    tgl = st.date_input(
        "Tanggal",
        key="tgl_" + form_key
    )

    if lokasi == "Rumah":

        jam_absen = st.text_input(
            "Jam Absen WFH",
            placeholder="Contoh: 07:45",
            key="jam_absen_" + form_key
        )

    else:

        masuk = st.text_input(
            "Jam Masuk",
            "07:30",
            key="masuk_" + form_key
        )

        keluar = st.text_input(
            "Jam Keluar",
            "16:00",
            key="keluar_" + form_key
        )

    uraian = st.text_area(
        "Uraian Kegiatan",
        key="uraian_" + form_key
    )

    output = st.text_area(
        "Output/Hasil",
        key="output_" + form_key
    )

    # ================= TOMBOL SIMPAN =================
    if st.button("Simpan Data", type="primary"):

        uid = str(uuid.uuid4())

        if lokasi == "Rumah":

            masuk = jam_absen
            keluar = "-"

            if waktu_absen == "Pagi":
                dur = 2.5

            elif waktu_absen == "Siang":
                dur = 2.5

            elif waktu_absen == "Sore":
                dur = 3

            else:
                dur = 0

        else:

            dur = hitung_durasi(masuk, keluar)

        if not uraian or not output:
            st.error("⚠️ Uraian dan Output wajib diisi!")

        elif lokasi != "Rumah" and dur == 0:
            st.error("⚠️ Jam tidak valid!")

        elif lokasi == "Rumah" and (foto is None or koordinat == ""):
            st.error("⚠️ Untuk Rumah, Foto dan GPS wajib ada!")

        else:

            link_foto = ""

            if lokasi == "Rumah":
                link_foto = upload_foto(foto)

            sheet.append_row([
                uid,
                safe(st.session_state.nama),
                safe(str(st.session_state.nip)),
                safe(st.session_state.jabatan),
                safe(st.session_state.unit),
                safe(tgl.strftime("%Y-%m-%d")),
                safe(masuk),
                safe(keluar),
                dur,
                safe(uraian),
                safe(output),
                safe(lokasi),
                safe(waktu_absen if lokasi == "Rumah" else "-"),
                safe(koordinat),
                safe(link_foto)
            ])

            load_data.clear()

            st.session_state.show_toast = True
            st.session_state.form_id += 1
            st.session_state.gps = ""

            st.rerun()

# ================= DATA =================
elif menu == "Data Kinerja":

    st.subheader("📋 Data Kinerja Pegawai")

    df = load_data()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    # ================= FORMAT DATA =================
    if "Durasi" in df.columns:

        df["Durasi"] = pd.to_numeric(
            df["Durasi"],
            errors="coerce"
        ).fillna(0)

    elif "Durasi" in df.columns:

        df["Durasi"] = (
            df["Durasi"]
            .astype(str)
            .str.strip()
            .str.replace(",", ".", regex=False)
        )

        df["Durasi"] = pd.to_numeric(
            df["Durasi"],
            errors="coerce"
        ).fillna(0)

        df["Durasi"] = df["Durasi"].astype(float)

    else:

        df["Durasi"] = df.apply(
            lambda r: hitung_durasi(
                r["Jam Masuk"],
                r["Jam Keluar"]
            ),
            axis=1
        )

    df["Tanggal"] = pd.to_datetime(
        df["Tanggal"],
        errors="coerce"
    )

    df = df.dropna(subset=["Tanggal"])

    # ================= FILTER ROLE =================

    if st.session_state.role in ["Admin", "Pimpinan"]:

        mode = st.radio(
            "Mode Data",
            ["Semua Data", "Data Saya"],
            horizontal=True
        )

        if mode == "Data Saya":

            df = df[
                df["NIP"].astype(str)
                == st.session_state.nip
            ]

    elif st.session_state.role == "Kasubbag":

        mode = st.radio(
            "Mode Data",
            ["Data Unit", "Data Saya"],
            horizontal=True
        )

        if mode == "Data Saya":

            df = df[
                df["NIP"].astype(str)
                == st.session_state.nip
            ]

        else:

            df = df[
                df["Unit"]
                == st.session_state.unit
            ]

    else:

        df = df[
            df["NIP"].astype(str)
            == st.session_state.nip
        ]

    # ================= RANGE TANGGAL =================
    start_default = df["Tanggal"].min()
    end_default = df["Tanggal"].max()

    today = date.today()

    if pd.isna(start_default):
        start_default = today
    else:
        start_default = pd.to_datetime(
            start_default
        ).date()

    if pd.isna(end_default):
        end_default = today
    else:
        end_default = pd.to_datetime(
            end_default
        ).date()

    tgl = st.date_input(
        "📅 Range Tanggal",
        value=(start_default, end_default)
    )

    if len(tgl) == 2:

        df = df[
            (df["Tanggal"] >= pd.to_datetime(tgl[0])) &
            (df["Tanggal"] <= pd.to_datetime(tgl[1]))
        ]

    # ================= FILTER PEGAWAI =================
    if st.session_state.role in [
        "Admin",
        "Pimpinan",
        "Kasubbag"
    ]:

        Pegawai = st.multiselect(
            "👤 Filter Pegawai",
            sorted(df["Nama"].unique())
        )

        if Pegawai:

            df = df[
                df["Nama"].isin(Pegawai)
            ]

    # ================= FILTER LOKASI =================
    lokasi_filter = st.multiselect(
        "📍 Filter Lokasi",
        sorted(df["Lokasi"].unique())
    )

    if lokasi_filter:
        df = df[df["Lokasi"].isin(lokasi_filter)]

    # ================= SUMMARY =================
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Data",
        len(df)
    )

    c2.metric(
        "Total Jam",
        round(df["Durasi"].sum(), 2)
    )

    c3.metric(
        "Total Hari",
        df["Tanggal"].nunique()
    )

    c4.metric(
        "Total Pegawai",
        df["Nama"].nunique()
    )

    st.divider()

    # ================= CARD DATA =================
    for i, row in df.iterrows():

        lokasi_color = "#22c55e"

        if row["Lokasi"] == "Rumah":
            lokasi_color = "#f59e0b"

        elif row["Lokasi"] == "Dinas Luar / SPT":
            lokasi_color = "#3b82f6"

        st.markdown(f"""
        <div style="
            background:white;
            padding:20px;
            border-radius:18px;
            margin-bottom:20px;
            border:1px solid #e5e7eb;
            box-shadow:0 2px 10px rgba(0,0,0,0.06);
        ">
        """, unsafe_allow_html=True)

        # ================= HEADER CARD =================
        colA, colB = st.columns([6,2])

        with colA:

            st.markdown(f"""
            ### 👤 {row['Nama']}
            📅 {row['Tanggal'].date()}
            """)
            
            st.caption(f"NIP: {row['NIP']}")

        with colB:

            st.markdown(f"""
            <div style="
                background:{lokasi_color};
                color:white;
                padding:10px;
                border-radius:999px;
                text-align:center;
                font-weight:bold;
                margin-top:15px;
            ">
                📍 {row['Lokasi']}
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # ================= ISI =================
        isi1, isi2 = st.columns(2)

        with isi1:

            st.markdown("#### 📝 Uraian Kegiatan")

            st.info(row["Uraian"])


        with isi2:

            st.markdown("#### 📦 Output / Hasil")

            st.success(row["Output"])


        # ================= INFO =================
        info1, info2, info3 = st.columns(3)

        with info1:
            st.info(f"⏱ Durasi: {row['Durasi']:.2f} Jam")

        with info2:

            if "Waktu Absen" in row and row["Waktu Absen"]:
                st.success(f"🕒 {row['Waktu Absen']}")

        with info3:

            if "Koordinat" in row and row["Koordinat"]:
                st.warning("📍 GPS Terdeteksi")

        # ================= FOTO =================
        if "Foto" in row and row["Foto"]:

            foto_data = str(row["Foto"])

            if len(foto_data) > 100:

                st.image("data:image/jpeg;base64," + foto_data)

            elif foto_data.startswith("http"):

                st.markdown(
                    f"[📸 Lihat Foto]({foto_data})"
                )

        # ================= TOMBOL =================
        btn1, btn2, btn3 = st.columns([8,1,1])

        if btn2.button(
            "✏️",
            key=f"edit{i}"
        ):

            st.session_state.edit = row

            st.rerun()

        if btn3.button(
            "🗑",
            key=f"del{i}"
        ):

            sheet.delete_rows(
                int(row["row"])
            )

            load_data.clear()

            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

    # ================= DOWNLOAD EXCEL =================
    st.subheader("📥 Download Data")

    df["NIP"] = df["NIP"].astype(str)

    excel = io.BytesIO()

    with pd.ExcelWriter(
        excel,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Data"
        )

        worksheet = writer.sheets["Data"]

        for row_excel in worksheet.iter_rows():

            for cell in row_excel:

                cell.alignment = Alignment(
                    wrap_text=True,
                    vertical="top"
                )

    excel.seek(0)

    st.download_button(
        label="📥 Download Excel",
        data=excel,
        file_name="data_kinerja.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
# ================= ADMIN =================
elif menu == "Admin":

    # Hanya admin yang boleh akses
    if st.session_state.role not in ["Admin", "Pimpinan"]:
        st.error("❌ Anda tidak memiliki akses.")
        st.stop()

    st.title("⚙️ Admin Panel")

    df = load_data()
    users_df = load_users()

    # ================= KPI ADMIN =================
    a1, a2, a3, a4 = st.columns(4)

    a1.metric(
        "👥 Total Pegawai",
        users_df["Nama"].nunique()
    )

    a2.metric(
        "📄 Total Kinerja",
        len(df)
    )

    a3.metric(
        "⏱ Total Jam",
        round(df["Durasi"].sum(), 2)
        if "Durasi" in df.columns else 0
    )

    a4.metric(
        "📅 Total Hari",
        df["Tanggal"].nunique()
        if "Tanggal" in df.columns else 0
    )

    st.divider()

    # ================= DATA USER =================
    st.subheader("👤 Data User")

    # Hilangkan kolom password
    users_tampil = users_df.drop(
        columns=["Password"],
        errors="ignore"
    )

    st.dataframe(
        users_tampil,
        use_container_width=True
    )

    st.divider()

    # ================= TAMBAH USER =================
    if st.session_state.role == "Admin":

        st.subheader("➕ Tambah User")

        with st.form("form_user"):

            nip_baru = st.text_input("NIP")

            nama_baru = st.text_input("Nama")

            jabatan_baru = st.text_input("Jabatan")

            unit_baru = st.selectbox(
                "Unit",
                [
                    "Sekretariat",
                    "SDM dan Parhubmas",
                    "Hukum dan Tekhnis Penyelenggaraan",
                    "Keuangan, Umum dan Logistik",
                    "Perencanaan, Data dan Informasi"
                ]
            )
            password_baru = st.text_input(
                "Password",
                type="password"
            )

            role_baru = st.selectbox(
                "Role",
                ["Pegawai", "Pimpinan", "Admin"]
            )

            simpan_user = st.form_submit_button(
                "Simpan User"
            )

            if simpan_user:

                if not nip_baru or not nama_baru:

                    st.error("⚠️ Lengkapi data user")

                else:

                    user_sheet.append_row([
                        nip_baru,
                        nama_baru,
                        jabatan_baru,
                        password_baru,
                        role_baru,
                        unit_baru
                    ])

                    load_users.clear()

                    st.success("✅ User berhasil ditambahkan")

                    st.rerun()