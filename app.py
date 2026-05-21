# ================= DATA =================
elif menu == "Data Kinerja":

    st.subheader("📋 Data Kinerja Pegawai")

    df = load_data()

    if df.empty:
        st.info("Belum ada data")
        st.stop()

    # ================= FORMAT DATA =================
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
    if st.session_state.role in ["Admin", "pimpinan"]:

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

    else:

        # Pegawai hanya melihat data sendiri
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
    if st.session_state.role in ["Admin", "pimpinan"]:

        pegawai = st.multiselect(
            "👤 Filter Pegawai",
            sorted(df["Nama"].unique())
        )

        if pegawai:
            df = df[df["Nama"].isin(pegawai)]

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

            if foto_data.startswith("data:image"):

                st.image(
                    foto_data,
                    width=250,
                    caption="📸 Dokumentasi Kegiatan"
                )

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