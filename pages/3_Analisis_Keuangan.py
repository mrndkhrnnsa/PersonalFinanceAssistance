import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from app_utils import fetch_data, get_financial_summary, load_budget_csv
import pandas as pd
import calendar
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.header("📊 Analisis Keuangan")

df = fetch_data()
if df.empty:
    st.warning("Belum ada data transaksi untuk dianalisis. Silahkan input transaksi terlebih dahulu di halaman Input Transaksi.")
    st.stop()

df["month_period"] = df["date"].dt.to_period("M")
df["month"] = df["month_period"].astype(str)

indonesian_months = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}
df["month_label"] = df["date"].dt.month.map(indonesian_months) + " " + df["date"].dt.year.astype(str)
df["year"] = df["date"].dt.year

budget = load_budget_csv()
allowed_categories = list(budget.keys()) if budget else ["Makanan", "Transport", "Belanja", "Hiburan", "Tabungan", "Lainnya"]

period_type = st.radio("Pilih Periode Analisis", ["Bulanan", "Tahunan"], horizontal=True)

if period_type == "Bulanan":
    month_map = (
        df[["month", "month_label"]]
        .drop_duplicates()
        .sort_values("month")
        .set_index("month")["month_label"]
        .to_dict()
    )
    label_to_month = {v: k for k, v in month_map.items()}

    available_month_labels = list(month_map.values())
    selected_month_label = st.selectbox("Pilih Bulan", available_month_labels)
    selected_month = label_to_month[selected_month_label]

    month_df = df[df["month"] == selected_month]
    summary = get_financial_summary(month_df)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Pendapatan", f"Rp {summary['total_income']:,.0f}")
    col2.metric("Total Pengeluaran", f"Rp {summary['total_expense']:,.0f}")
    col3.metric("Saldo", f"Rp {summary['balance']:,.0f}")

    # 1. Budget vs Actual Spending Bar Chart
    st.subheader("1️⃣ Anggaran vs Pengeluaran Aktual")
    actual = (
        month_df[month_df["category"] == "Pengeluaran"]
        .groupby("subcategory")["amount"]
        .sum()
        .reindex(allowed_categories, fill_value=0)
    )
    budget_series = pd.Series(budget)
    compare_df = pd.DataFrame({
        "Kategori": allowed_categories,
        "Realisasi": actual.values,
        "Anggaran": budget_series.reindex(allowed_categories, fill_value=0).values
    })
    compare_df = compare_df.melt(id_vars="Kategori", value_vars=["Realisasi", "Anggaran"], var_name="Tipe", value_name="Jumlah")
    fig = px.bar(
        compare_df, x="Kategori", y="Jumlah", color="Tipe", barmode="group",
        color_discrete_sequence=["#e43434","#328ed0" ])

    st.plotly_chart(fig, use_container_width=True)

    # 2. Spending Distribution Pie Chart
    st.subheader("2️⃣ Distribusi Pengeluaran")
    spend_dist = (
        month_df[month_df["category"] == "Pengeluaran"]
        .groupby("subcategory")["amount"]
        .sum()
        .reindex(allowed_categories, fill_value=0)
    )
    spend_dist_nonzero = spend_dist[spend_dist > 0]
    if spend_dist_nonzero.sum() > 0:
        fig2 = px.pie(
            names=spend_dist_nonzero.index,
            values=spend_dist_nonzero.values,
            color_discrete_sequence=px.colors.diverging.RdBu_r
        )
        fig2.update_traces(textposition='inside', textinfo='percent+label')
        fig2.update_layout(height=400, width=400, legend_title="Sub-kategori",)
        st.plotly_chart(fig2)
    else:
        st.info("Belum ada data pengeluaran untuk bulan ini.")

    # 3. Calendar Heatmap of Daily Spending (Blues)
    st.subheader("3️⃣ Heatmap Kalender Pengeluaran Harian")
    month_df["day"] = month_df["date"].dt.day
    daily_spending = (
        month_df[month_df["category"] == "Pengeluaran"]
        .groupby("day")["amount"]
        .sum()
    )

    year, month = month_df["date"].dt.year.iloc[0], month_df["date"].dt.month.iloc[0]
    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)
    heatmap = np.zeros((len(month_days), 7))
    day_labels = np.full((len(month_days), 7), "", dtype=object)
    for week_idx, week in enumerate(month_days):
        for day_idx, day in enumerate(week):
            if day != 0:
                heatmap[week_idx, day_idx] = daily_spending.get(day, 0)
                day_labels[week_idx, day_idx] = str(day)
            else:
                heatmap[week_idx, day_idx] = np.nan
                day_labels[week_idx, day_idx] = ""

    fig3 = go.Figure(
        data=go.Heatmap(
            z=heatmap,
            x=["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"],
            y=[f"Minggu ke-{i+1}" for i in range(len(month_days))],
            colorscale="Blues",
            colorbar=dict(title="Jumlah (Rp)"),
            hoverinfo="z"
        )
    )

    for week_idx, week in enumerate(month_days):
        for day_idx, day in enumerate(week):
            if day != 0:
                value = heatmap[week_idx, day_idx]
                fig3.add_annotation(
                    x=day_idx, y=week_idx,
                    text=f"{int(day)}<br>{int(value):,}",
                    showarrow=False,
                    font=dict(size=10, color="black"),
                    xanchor="center", yanchor="middle"
                )
    fig3.update_layout(
        xaxis=dict(side="top"),
        height=600, width=600
    )
    st.plotly_chart(fig3)

else:
    available_years = sorted(df["year"].unique().tolist())
    selected_year = st.selectbox("Pilih Tahun", available_years)
    year_df = df[df["date"].dt.year == selected_year]

    # 1. Monthly Cashflow Summary Line Chart
    st.subheader("1️⃣ Rekapitulasi Bulanan")
    monthly_cashflow = (
        year_df.groupby(year_df["date"].dt.to_period("M")).apply(
            lambda x: x[x["category"] == "Pendapatan"]["amount"].sum() - x[x["category"] == "Pengeluaran"]["amount"].sum()
        )
    )
    monthly_cashflow.index = [i.strftime("%B %Y") for i in monthly_cashflow.index]
    fig4 = px.line(
        x=monthly_cashflow.index,
        y=monthly_cashflow.values,
        markers=True,
        labels={"x": "Bulan", "y": "Alur Kas (Rp)"},
        color_discrete_sequence=px.colors.diverging.RdBu_r
    )
    st.plotly_chart(fig4, use_container_width=True)

    # 2. Pendapatan vs Pengeluaran per Bulan (Blue for Pendapatan, Red for Pengeluaran)
    st.subheader("2️⃣ Pendapatan vs Pengeluaran per Bulan")
    monthly_summary = (
        year_df.groupby([year_df["date"].dt.to_period("M"), "category"])["amount"]
        .sum()
        .reset_index()
    )
    monthly_summary["date"] = monthly_summary["date"].dt.to_timestamp()
    monthly_summary.rename(columns={"date": "Bulan", "category": "Kategori", "amount": "Jumlah"}, inplace=True)
    fig = px.bar(
        monthly_summary,
        x="Bulan",
        y="Jumlah",
        color="Kategori",
        barmode="group",
        color_discrete_map={"Pendapatan": "#328ed0", "Pengeluaran": "#e43434"}
    )
    fig.update_layout(
        xaxis_title="Bulan",
        yaxis_title="Jumlah (Rp)",
        legend_title="Kategori",
    )
    st.plotly_chart(fig, use_container_width=True)

    # 3. Spending by Sub-Category Over the Year
    st.subheader("3️⃣ Distribusi Pengeluaran Tahunan berdasarkan Kategori")
    spend_by_cat = (
        year_df[year_df["category"] == "Pengeluaran"]
        .groupby([year_df["date"].dt.to_period("M"), "subcategory"])["amount"]
        .sum()
        .unstack(fill_value=0)
        .reindex(columns=allowed_categories, fill_value=0)
    )
    spend_by_cat.index = [i.strftime("%B %Y") for i in spend_by_cat.index]
    if not spend_by_cat.empty:
        spend_by_cat_reset = spend_by_cat.reset_index().rename(columns={"index": "Bulan"})
        spend_by_cat_melt = spend_by_cat_reset.melt(id_vars="Bulan", var_name="Kategori", value_name="Jumlah")
        fig5 = px.bar(
            spend_by_cat_melt,
            x="Bulan",
            y="Jumlah",
            color="Kategori",
            barmode="group",
            title=f"Distribusi Pengeluaran Tahunan berdasarkan Kategori - {selected_year}",
            color_discrete_sequence=px.colors.sequential.RdBu_r
        )
        fig5.update_layout(xaxis_title="Bulan", yaxis_title="Jumlah (Rp)", legend_title="Sub-kategori",)
        st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("Belum ada data pengeluaran untuk tahun ini.")
