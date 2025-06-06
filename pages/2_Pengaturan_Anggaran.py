import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import requests
import re
from app_utils import load_csv, save_budget_csv, get_historical_average_by_category

st.header("🧮 Pengaturan Anggaran")

SUBCATEGORIES = ["Makanan", "Transport", "Belanja", "Hiburan", "Tabungan", "Lainnya"]
category_map = {
    "food": "Makanan", "makanan": "Makanan", "transport": "Transport", "transportasi": "Transport",
    "shopping": "Belanja", "belanja": "Belanja", "entertainment": "Hiburan", "hiburan": "Hiburan",
    "savings": "Tabungan", "tabungan": "Tabungan", "other": "Lainnya", "misc": "Lainnya", "lainnya": "Lainnya"
}

# Calculate budget based on historical averages and user input
transactions_df = load_csv()
transactions_df["Tanggal"] = pd.to_datetime(transactions_df["Tanggal"], errors="coerce")
historical_averages = get_historical_average_by_category(transactions_df, SUBCATEGORIES, months_back=100)
monthly_income = 0
if not transactions_df.empty:
    income_per_month = (
        transactions_df[transactions_df["Kategori"] == "Pendapatan"]
        .groupby(transactions_df["Tanggal"].dt.to_period("M"))["Jumlah (Rp)"]
        .sum()
    )
    if not income_per_month.empty:
        monthly_income = income_per_month.mean()

savings_goal = st.number_input("Target Total Tabungan (Rp)", min_value=0, step=50000)
free_text_goal = st.text_area("Catatan Tambahan (misal: 'kurangi pengeluaran makanan', 'nabung untuk liburan')")

if st.button("Hasilkan Anggaran AI"):
    with st.spinner("Lagi dibikinin anggaran nya nih...sabar dikit, biar akhir bulan nggak drama! "):
        history_str = "\n".join([f"- {cat}: Rp{amount:,.0f}" for cat, amount in historical_averages.items()])
        prompt = (
            f"Kamu adalah asisten keuangan. Ini adalah pengeluaran rata-rata bulanan berdasarkan seluruh data historis:\n{history_str}\n\n"
            f"Pendapatan bulan ini diperkirakan Rp{monthly_income:,.0f}. Target tabungan: Rp{savings_goal:,.0f}.\n"
            f"{free_text_goal}\n"
            "Buat anggaran bulanan yang masuk akal. Hanya gunakan kategori: Makanan, Transport, Belanja, Hiburan, Tabungan, Lainnya."
            "Jawab dalam format tabel markdown dan gunakan Bahasa Indonesia."
        )

        api_key = "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"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": 'deepseek/deepseek-chat-v3-0324',
            "messages": [{"role": "user", "content": prompt}]
        }

        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)

    if response.status_code == 200:
        ai_text = response.json()['choices'][0]['message']['content']
        st.subheader("🧠 Rekomendasi Anggaran dari AI")

        parsed_budget = {}
        parsed_percentages = {}
        in_table = False
        for line in ai_text.splitlines():
            if re.match(r"\s*\|", line) and not re.match(r"\s*\|[\s\-|]+\|", line):
                cols = [c.strip(" *") for c in line.strip().split("|")[1:-1]]
                if len(cols) >= 2:
                    category = cols[0].lower()
                    amount_str = next((c for c in cols[1:] if re.search(r"\d", c)), None)
                    percent_str = next((c for c in cols[1:] if "%" in c), None)
                    matched = None
                    for allowed in SUBCATEGORIES:
                        if allowed.lower() in category:
                            matched = allowed
                            break
                    if not matched:
                        for key in category_map:
                            if key in category:
                                matched = category_map[key]
                                break
                    if not matched or not amount_str:
                        continue
                    try:
                        amount = float(amount_str.replace("$", "").replace(",", "").replace("%", "").strip())
                        parsed_budget[matched] = amount
                        if percent_str:
                            try:
                                parsed_percentages[matched] = float(percent_str.replace("%", "").replace(",", "").strip())
                            except ValueError:
                                parsed_percentages[matched] = None
                        else:
                            parsed_percentages[matched] = None
                    except ValueError:
                        continue

        if parsed_budget:
            st.session_state.budget_inputs = {cat: parsed_budget.get(cat, 0.0) for cat in SUBCATEGORIES}
            st.session_state.budget_percentages = {cat: parsed_percentages.get(cat, None) for cat in SUBCATEGORIES}
            st.success("Anggaran dari AI sudah jadi! Ubah sesuai kebutuhan dan simpan ya.")
        else:
            st.warning("⚠️ Oops! Anggaran dari AI belum bisa dibaca. Silakan revisi atau coba lagi.")
    else:
        st.error("❌ Oops! AI lagi bingung dan belum bisa menjawab. Coba ulangi beberapa saat lagi ya.")

if "budget_inputs" in st.session_state:
    st.markdown("✏️ Nilai di bawah bisa kamu sesuaikan sebelum disimpan:")
    for category in SUBCATEGORIES:
        percent = st.session_state.get("budget_percentages", {}).get(category)
        label = f"{category}"
        if percent is not None:
            label += f" ({percent:.2f}%)"
        st.session_state.budget_inputs[category] = st.number_input(
            label, value=st.session_state.budget_inputs.get(category, 0.0), step=50000.0, key=f"budget_{category}"
        )
    if st.button("💾 Simpan Anggaran"):
        save_budget_csv(st.session_state.budget_inputs)
        st.success("✅ Anggaran berhasil disimpan!")
