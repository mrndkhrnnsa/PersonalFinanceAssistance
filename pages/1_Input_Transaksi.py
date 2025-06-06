import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from app_utils import load_csv, save_to_csv
import pandas as pd

st.header("💸 Input Transaksi")
tabs = st.tabs([' ➕ Transaksi Baru', ' 📄 Riwayat Transaksi'])

CATEGORIES = ["Pendapatan", "Pengeluaran"]
SUBCATEGORIES = ["Gaji", "Bonus", "Makanan", "Transport", "Belanja", "Hiburan", "Tabungan", "Lainnya"]
PAYMENT = ["Cash", "Debit", "Credit", "E-Wallet"]

with tabs[0]:
    st.subheader("Input Manual Transaksi")
    with st.form("input_form"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Tanggal")
            amount = st.number_input("Jumlah (Rp)", min_value=0.0, step=1000.0)
            category = st.selectbox("Kategori", CATEGORIES)
        with col2:
            description = st.text_input("Deskripsi")
            payment_method = st.selectbox("Metode Pembayaran", PAYMENT)
            subcategory = st.selectbox("Sub-kategori", SUBCATEGORIES)
        note = st.text_area("Catatan (opsional)", placeholder="Tambahkan catatan jika perlu")

        submit_button = st.form_submit_button("💾 Simpan Transaksi")
        if submit_button:
            if not description:
                st.error("Mohon isi deskripsi transaksi!")
            else:
                try:
                    new_row = {
                        "Tanggal": pd.to_datetime(date).strftime("%Y-%m-%d"),
                        "Deskripsi": description,
                        "Jumlah (Rp)": float(amount),
                        "Kategori": category,
                        "Sub-kategori": subcategory,
                        "Metode Pembayaran": payment_method,
                        "Catatan": note if note else ""
                    }
                    
                    # Load existing data
                    df = load_csv()
                    
                    # Add new row
                    new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    
                    # Save and refresh
                    if save_to_csv(new_df):
                        st.session_state.need_refresh = True
                        st.success("✅ Transaksi berhasil disimpan!")
                    else:
                        st.error("Gagal menyimpan transaksi. Silakan coba lagi.")
                except Exception as e:
                    st.error(f"Terjadi kesalahan: {str(e)}")

    st.subheader("Upload CSV Transaksi")
    st.markdown(
        """
        <b>Pastikan file CSV Anda memiliki kolom berikut:</b>
        <ul>
            Tanggal, Deskripsi, Jumlah (Rp), Kategori, Sub-kategori, Metode Pembayaran, Catatan
        </ul>
        """,
        unsafe_allow_html=True
    )
    template_df = pd.DataFrame(columns=[
        "Tanggal", "Deskripsi", "Jumlah (Rp)", "Kategori", "Sub-kategori", "Metode Pembayaran", "Catatan"
    ])
    csv = template_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Template CSV",
        data=csv,
        file_name="template_transaksi.csv",
        mime="text/csv"
    )

    uploaded_file = st.file_uploader("Pilih file CSV", type=["csv"])
    if uploaded_file is not None:
        uploaded_df = pd.read_csv(uploaded_file)
        expected_cols = [
            "Tanggal", "Deskripsi", "Jumlah (Rp)", "Kategori",
            "Sub-kategori", "Metode Pembayaran", "Catatan"
        ]
        uploaded_df.columns = [col.strip() for col in uploaded_df.columns]
        missing_cols = [col for col in expected_cols if col not in uploaded_df.columns]
        if missing_cols:
            st.error(f"Kolom berikut tidak ditemukan di file CSV: {missing_cols}")
        else:
            uploaded_df = uploaded_df[expected_cols]
            uploaded_df["Tanggal"] = pd.to_datetime(uploaded_df["Tanggal"], errors="coerce")
            uploaded_df = uploaded_df.dropna(subset=["Tanggal"])
            existing_df = load_csv()
            combined_df = pd.concat([existing_df, uploaded_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates()
            save_to_csv(combined_df)
            st.success("✅ Data dari CSV berhasil diunggah dan disimpan!")

with tabs[1]:
    st.write("Daftar Transaksi:")
    
    # Load and prepare data
    df = load_csv()
    
    if df.empty:
        st.info("Belum ada transaksi yang ditemukan.")
    else:
        # Convert and clean date data
        df["Tanggal"] = pd.to_datetime(df["Tanggal"])
        df = df.sort_values("Tanggal", ascending=False).reset_index(drop=True)
        
        # Set min and max dates
        min_date = df["Tanggal"].min().date()
        max_date = df["Tanggal"].max().date()

        # Date filter columns
        col1, col2 = st.columns([2, 2])
        with col1:
            start_date = st.date_input("Tanggal Awal", value=min_date)
        with col2:
            end_date = st.date_input("Tanggal Akhir", value=max_date)
        
        if end_date < start_date:
            st.warning("Tanggal Akhir tidak boleh sebelum Tanggal Awal")
            end_date = start_date

        # Filter columns
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            kategori_filter = st.selectbox("Filter Kategori", ["Semua"] + sorted(df["Kategori"].dropna().unique().tolist()))
        with col2:
            subkategori_filter = st.selectbox("Filter Sub-kategori", ["Semua"] + sorted(df["Sub-kategori"].dropna().unique().tolist()))
        with col3:
            metode_filter = st.selectbox("Filter Metode", ["Semua"] + sorted(df["Metode Pembayaran"].dropna().unique().tolist()))
        with col4:
            search = st.text_input("Cari Deskripsi")

        # Apply filters
        filtered_df = df.copy()

        # Apply date filter
        filtered_df = filtered_df[
            (filtered_df["Tanggal"].dt.date >= start_date) &
            (filtered_df["Tanggal"].dt.date <= end_date)
        ]
        
        # Apply category filters
        if kategori_filter != "Semua":
            filtered_df = filtered_df[filtered_df["Kategori"] == kategori_filter]
        if subkategori_filter != "Semua":
            filtered_df = filtered_df[filtered_df["Sub-kategori"] == subkategori_filter]
        if metode_filter != "Semua":
            filtered_df = filtered_df[filtered_df["Metode Pembayaran"] == metode_filter]
        
        # Apply search filter
        if search:
            filtered_df = filtered_df[filtered_df["Deskripsi"].str.contains(search, case=False, na=False)]
        
        # Show data in editor
        if len(filtered_df) == 0:
            st.info("Tidak ada transaksi dalam rentang tanggal yang dipilih.")
        else:
            # Show data editor with current filters applied
            edited_df = st.data_editor(
                filtered_df,
                num_rows="dynamic",
                use_container_width=True,
                key="data_editor",
                column_order=[
                    "Tanggal", "Deskripsi", "Jumlah (Rp)", "Kategori",
                    "Sub-kategori", "Metode Pembayaran", "Catatan"
                ]
            )
            
            # Action buttons
            col1, col2 = st.columns([2,2])
            with col1:
                if st.button("💾 Simpan Perubahan"):
                    try:
                        save_to_csv(edited_df)
                        st.success("✅ Perubahan berhasil disimpan!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan perubahan: {str(e)}")