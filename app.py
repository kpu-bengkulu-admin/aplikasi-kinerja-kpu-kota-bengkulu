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
FOLDER_ID = "1c2dL7ojqrQPqt7SjYCeI7L_NBhRApped"

import base64
from PIL import Image
import io

def upload_foto(file):
    if file is None: return ""
    
    try:
        # 1. Buka foto dan perkecil ukurannya (agar tidak membebani Spreadsheet)
        img = Image.open(file)
        img.thumbnail((400, 400))  # Perkecil ke 400px
        
        # 2. Ubah foto menjadi teks (Base64)
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=70) # Kompres kualitas ke 70%
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # 3. Kita tidak upload ke Drive, tapi kirim teks ini kembali
        # Kita buat link tiruan yang isinya data foto
        return f"data:image/jpeg;base64,{img_str}"

    except Exception as e:
        st.error(f"Gagal memproses foto: {e}")
        return ""


# ================= CONFIG =================
st.set_page_config(
    page_title="E-Kinerja KPU Kota Bengkulu",
    page_icon="logo.png",
    layout="wide"
)

st.sidebar.image("logo.png", width=100)

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
menu = st.sidebar.radio("Menu", ["Dashboard", "Input", "Data Kinerja", "Admin"])

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

# ================= FILTER ROLE =================

if st.session_state.role in ["admin", "pimpinan"]:

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

else:
    # Pegawai hanya melihat data sendiri
    df = df[df["NIP"].astype(str) == st.session_state.nip]

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
    output = st.text_area("Output/Hasil")

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
        
        # PERBAIKAN 1: Menampilkan Output di daftar utama (agar Enter terlihat)
        if "Output" in row and row["Output"]:
            c1.markdown(f"**Output:** \n{row['Output']}")

        if "Koordinat" in row and row["Koordinat"]:
            c1.write(f"📍 {row['Koordinat']}")

        # --- BAGIAN PERBAIKAN FOTO ---
        if "Foto" in row and row.get("Foto"):
            foto_data = str(row["Foto"])
            if foto_data.startswith("data:image"):
                # Menambahkan caption agar lebih rapi
                c1.image(foto_data, width=250, caption="Dokumentasi")
            elif foto_data.startswith("http"):
                c1.markdown(f"[📸 Lihat Foto]({foto_data})")
        # --- SELESAI ---

        c2.write(f"{row['Durasi']:.2f} jam")

        if c3.button("✏️", key=f"edit{i}"):
            st.session_state.edit = row
            st.rerun()

        if c4.button("🗑", key=f"del{i}"):
            sheet.delete_rows(int(row["row"]))
            st.rerun()


    # DOWNLOAD
    st.divider()

    from openpyxl.styles import Alignment

    df["NIP"] = df["NIP"].astype(str)

    excel = io.BytesIO()

    with pd.ExcelWriter(excel, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")

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