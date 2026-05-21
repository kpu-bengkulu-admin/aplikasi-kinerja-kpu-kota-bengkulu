import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import io
import base64
from PIL import Image
from openpyxl.styles import Alignment

# ================= CONFIG =================
st.set_page_config(
    page_title="E-Kinerja KPU Kota Bengkulu",
    page_icon="logo_kpu.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= STYLE =================
st.markdown("""
<style>

/* Header */
header {
    visibility: visible !important;
    height: 60px !important;
    background: transparent !important;
}

/* Hilangkan menu dan footer */
#MainMenu {
    visibility: hidden !important;
}

footer {
    visibility: hidden !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    min-width: 260px !important;
    width: 260px !important;
    background:#0f172a !important;
}

/* Sidebar Text */
[data-testid="stSidebar"] * {
    color: white !important;
}

/* Input sidebar */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea {
    color: black !important;
    background-color: white !important;
    -webkit-text-fill-color: black !important;
}

/* Tombol */
.stButton button {
    background-color: #ef4444 !important;
    color: white !important;
    border-radius: 8px !important;
}

</style>
""", unsafe_allow_html=True)

# ================= SESSION =================
if "gps" not in st.session_state:
    st.session_state.gps = ""

# ================= DRIVE =================
FOLDER_ID = "1c2dL7ojqrQPqt7SjYCeI7L_NBhRApped"

# ================= FOTO =================
def upload_foto(file):

    if file is None:
        return ""

    try:
        img = Image.open(file)

        img.thumbnail((400, 400))

        buffered = io.BytesIO()

        img.save(
            buffered,
            format="JPEG",
            quality=70
        )

        img_str = base64.b64encode(
            buffered.getvalue()
        ).decode()

        return f"data:image/jpeg;base64,{img_str}"

    except Exception as e:
        st.error(f"Gagal memproses foto: {e}")
        return ""

# ================= GOOGLE =================
@st.cache_resource
def connect():

    info = dict(st.secrets["connections"]["gsheets"])

    info["private_key"] = info["private_key"].replace(
        "\\n",
        "\n"
    )

    creds = Credentials.from_service_account_info(
        info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ],
    )

    return gspread.authorize(creds).open_by_key(
        st.secrets["SPREADSHEET_ID"]
    )

# ================= SPREADSHEET =================
try:

    spreadsheet = connect()

    sheet = spreadsheet.worksheet("data_kinerja")

except Exception as e:

    st.error(f"Gagal koneksi Spreadsheet: {e}")
    st.stop()

# ================= USERS =================
try:

    user_sheet = spreadsheet.worksheet("users")

except gspread.exceptions.WorksheetNotFound:

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

    st.error(f"Gagal mengakses users: {e}")
    st.stop()

# ================= HELPER =================
def safe(x):
    return "" if x is None else str(x)

@st.cache_data(ttl=5)
def load_data():

    df = pd.DataFrame(sheet.get_all_records())

    if not df.empty:
        df["row"] = range(2, len(df)+2)

    return df

@st.cache_data(ttl=5)
def load_users():
    return pd.DataFrame(user_sheet.get_all_records())

def parse_jam(x):

    try:
        h, m = str(x).replace(".", ":").split(":")
        return int(h) * 60 + int(m)

    except:
        return None

def hitung_durasi(masuk, keluar):

    jm = parse_jam(masuk)
    jk = parse_jam(keluar)

    if jm and jk and jk > jm:
        return round((jk-jm)/60, 2)

    return 0

# ================= LOGIN =================
if "login" not in st.session_state:
    st.session_state.login = False

users = load_users()

if not st.session_state.login:

    st.title("🔐 Login E-Kinerja KPU Kota Bengkulu")

    nip = st.text_input("NIP")

    pw = st.text_input(
        "Password",
        type="password"
    )

    if st.button("Login"):

        cek = users[
            (users["NIP"].astype(str) == str(nip)) &
            (users["Password"].astype(str) == str(pw))
        ]

        if not cek.empty:

            u = cek.iloc[0]

            st.session_state.login = True
            st.session_state.nama = u["Nama"]
            st.session_state.nip = str(u["NIP"])
            st.session_state.jabatan = u["Jabatan"]
            st.session_state.role = u["Role"]

            st.rerun()

        else:
            st.error("Login gagal")

    st.stop()

# ================= SIDEBAR =================
st.sidebar.image("logo_kpu.png", width=100)

st.sidebar.title(st.session_state.nama)

st.sidebar.markdown(
    f"""
    <p style='margin-top:-10px;color:gray;'>
    {st.session_state.role}
    </p>
    """,
    unsafe_allow_html=True
)

menu = st.sidebar.radio(
    "Menu",
    ["Dashboard", "Input", "Data Kinerja", "Admin"]
)

if st.sidebar.button("Logout"):

    st.session_state.clear()

    st.rerun()

# ================= EDIT =================
if "edit" in st.session_state:

    ed = st.session_state.edit

    st.sidebar.divider()

    st.sidebar.subheader("✏️ Edit Data")

    st.sidebar.info(
        f"Mengedit baris: {ed['row']}"
    )

    new_masuk = st.sidebar.text_input(
        "Jam Masuk",
        ed["Jam Masuk"],
        key="edit_masuk"
    )

    new_keluar = st.sidebar.text_input(
        "Jam Keluar",
        ed["Jam Keluar"],
        key="edit_keluar"
    )

    new_uraian = st.sidebar.text_area(
        "Uraian",
        ed["Uraian"],
        key="edit_uraian"
    )

    new_output = st.sidebar.text_area(
        "Output",
        ed["Output"],
        key="edit_output"
    )

    col1, col2 = st.sidebar.columns(2)

    if col1.button("Update ✅"):

        dur = hitung_durasi(
            new_masuk,
            new_keluar
        )

        try:

            row_idx = int(ed["row"])

            sheet.update(
                f"E{row_idx}:J{row_idx}",
                [[
                    new_masuk,
                    new_keluar,
                    dur,
                    new_uraian,
                    new_output,
                    ed["Lokasi"]
                ]]
            )

            load_data.clear()

            st.sidebar.success(
                "Data berhasil diperbarui"
            )

            del st.session_state.edit

            st.rerun()

        except Exception as e:

            st.sidebar.error(f"Error: {e}")

    if col2.button("Batal ❌"):

        del st.session_state.edit

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

    # ROLE
    if st.session_state.role == "Admin":

        pilihan_data = st.selectbox(
            "Pilih Data",
            ["Semua Pegawai", "Data Pribadi"]
        )

        if pilihan_data == "Data Pribadi":
            df = df[
                df["Nama"] == st.session_state.nama
            ]

    else:

        df = df[
            df["Nama"] == st.session_state.nama
        ]

    # TANGGAL
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
        "Range Tanggal",
        value=(start_default, end_default)
    )

    if len(tgl) == 2:

        df = df[
            (df["Tanggal"] >= pd.to_datetime(tgl[0])) &
            (df["Tanggal"] <= pd.to_datetime(tgl[1]))
        ]

    # FILTER
    pegawai = st.multiselect(
        "Pegawai",
        sorted(df["Nama"].unique())
    )

    lokasi = st.multiselect(
        "Lokasi",
        sorted(df["Lokasi"].unique())
    )

    if pegawai:
        df = df[df["Nama"].isin(pegawai)]

    if lokasi:
        df = df[df["Lokasi"].isin(lokasi)]

    # CARD
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total", len(df))

    c2.metric(
        "Jam",
        round(df["Durasi"].sum(), 2)
    )

    c3.metric(
        "Hari",
        df["Tanggal"].nunique()
    )

    c4.metric(
        "Pegawai",
        df["Nama"].nunique()
    )

    # GRAFIK
    st.bar_chart(
        df.groupby("Nama")["Durasi"].sum()
    )

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

    # ================= WFH =================
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

    # ================= FORM =================
    tgl = st.date_input("Tanggal")

    masuk = st.text_input(
        "Jam Masuk",
        "07:30"
    )

    keluar = st.text_input(
        "Jam Keluar",
        "16:00"
    )

    uraian = st.text_area(
        "Uraian Kegiatan"
    )

    output = st.text_area(
        "Output / Hasil"
    )

    # ================= SIMPAN =================
    if st.button(
        "Simpan Data",
        type="primary"
    ):

        dur = hitung_durasi(
            masuk,
            keluar
        )

        if not uraian or not output:

            st.error(
                "⚠️ Uraian dan output wajib diisi"
            )

        elif dur == 0:

            st.error(
                "⚠️ Jam tidak valid"
            )

        elif lokasi == "Rumah" and (
            foto is None or koordinat == ""
        ):

            st.error(
                "⚠️ Foto dan GPS wajib untuk WFH"
            )

        else:

            link_foto = ""

            if lokasi == "Rumah":
                link_foto = upload_foto(foto)

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

                safe(waktu_absen),

                safe(koordinat),

                safe(link_foto)

            ])

            load_data.clear()

            st.success(
                f"🎉 Data {lokasi} berhasil disimpan"
            )

            import time
            time.sleep(1)

            st.rerun()

# ================= DATA =================
elif menu == "Data Kinerja":

    df = load_data()

    if df.empty:

        st.info("Belum ada data")

        st.stop()

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

    # ROLE
    if st.session_state.role in [
        "Admin",
        "pimpinan"
    ]:

        mode = st.radio(
            "Mode Data",
            ["Semua Data", "Data Saya"]
        )

        if mode == "Data Saya":

            df = df[
                df["NIP"].astype(str)
                == st.session_state.nip
            ]

    else:

        df = df[
            df["NIP"].astype(str)
            == st.session_state.nip
        ]

    # FILTER TANGGAL
    tgl = st.date_input(
        "Filter Tanggal",
        value=(
            df["Tanggal"].min(),
            df["Tanggal"].max()
        )
    )

    if len(tgl) == 2:

        df = df[
            (df["Tanggal"] >= pd.to_datetime(tgl[0])) &
            (df["Tanggal"] <= pd.to_datetime(tgl[1]))
        ]

    # TAMPIL DATA
    for i, row in df.iterrows():

        c1, c2, c3, c4 = st.columns([5,2,1,1])

        c1.write(
            f"**{row['Nama']}** - "
            f"{row['Tanggal'].date()}"
        )

        c1.caption(row["Uraian"])

        # OUTPUT
        if "Output" in row and row["Output"]:

            c1.markdown(
                f"**Output:** \n{row['Output']}"
            )

        # WAKTU ABSEN
        if (
            "Waktu Absen" in row and
            row["Waktu Absen"] not in ["", "-"]
        ):

            c1.write(
                f"🕒 {row['Waktu Absen']}"
            )

        # KOORDINAT
        if "Koordinat" in row and row["Koordinat"]:

            c1.write(
                f"📍 {row['Koordinat']}"
            )

        # FOTO
        if "Foto" in row and row["Foto"]:

            foto_data = str(row["Foto"])

            if foto_data.startswith("data:image"):

                c1.image(
                    foto_data,
                    width=250,
                    caption="Dokumentasi"
                )

        c2.write(
            f"{row['Durasi']:.2f} jam"
        )

        # EDIT
        if c3.button("✏️", key=f"edit{i}"):

            st.session_state.edit = row

            st.rerun()

        # HAPUS
        if c4.button("🗑", key=f"del{i}"):

            sheet.delete_rows(
                int(row["row"])
            )

            st.rerun()

    # DOWNLOAD
    st.divider()

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

        workbook = writer.book

        worksheet = writer.sheets["Data"]

        for row in worksheet.iter_rows():

            for cell in row:

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

    if st.session_state.role != "Admin":

        st.error("Akses ditolak")

        st.stop()

    nip = st.text_input("NIP")

    nama = st.text_input("Nama")

    jab = st.text_input("Jabatan")

    pw = st.text_input("Password")

    role = st.selectbox(
        "Role",
        ["pegawai", "Admin", "pimpinan"]
    )

    if st.button("Tambah User"):

        user_sheet.append_row([
            nip,
            nama,
            jab,
            pw,
            role
        ])

        st.success("User ditambahkan")