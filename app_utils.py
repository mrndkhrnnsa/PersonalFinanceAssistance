# Import necessary libraries
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import requests
import re
from transformers import pipeline
import json
import matplotlib.pyplot as plt

# Data Directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
transactions_data = os.path.join(DATA_DIR, "transactions.csv")
expected_cols = [
    "Tanggal", "Deskripsi", "Jumlah (Rp)", "Kategori",
    "Sub-kategori", "Metode Pembayaran", "Catatan"
]

# Function to save DataFrame to CSV
def save_to_csv(df):
    try:
        # Create data directory if it doesn't exist
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # If df is empty, create a new one with correct columns
        if df is None or df.empty:
            df = pd.DataFrame(columns=expected_cols)
        
        # Ensure all columns exist
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        
        # Convert date column to datetime
        df["Tanggal"] = pd.to_datetime(df["Tanggal"])
        
        # Sort by date descending
        df = df.sort_values("Tanggal", ascending=False)
        
        # Save to CSV with proper date format
        df.to_csv(transactions_data, index=False, date_format="%Y-%m-%d")
        print(f"Data saved to {transactions_data}")  # Debug print
        
        return True
    except Exception as e:
        print(f"Error saving data: {str(e)}")  # Debug print
        st.error(f"Error saving data: {str(e)}")
        return False

# Function to load DataFrame from CSV
def load_csv():
    try:
        if os.path.exists(transactions_data):
            print(f"Loading data from {transactions_data}")  # Debug print
            df = pd.read_csv(transactions_data)
            
            # Ensure all expected columns exist
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = ""
            
            # Reorder columns to match expected order
            df = df[expected_cols]
            
            # Convert date column properly
            df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce")
            df = df.dropna(subset=["Tanggal"])
            
            # Sort by date
            df = df.sort_values("Tanggal", ascending=False).reset_index(drop=True)
            
            print(f"Loaded {len(df)} transactions")  # Debug print
            return df
        else:
            print("Creating new transaction file")  # Debug print
            df = pd.DataFrame(columns=expected_cols)
            # Save empty DataFrame to create the file
            df.to_csv(transactions_data, index=False)
            return df
    except Exception as e:
        print(f"Error loading data: {str(e)}")  # Debug print
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame(columns=expected_cols)

# Function to save budget dictionary to CSV
def save_budget_csv(budget_dict):
    budget_file = os.path.join(DATA_DIR, "budget.csv")
    try:
        # Create data directory if it doesn't exist
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Create DataFrame from budget dictionary
        if not budget_dict:
            # If empty, create with default categories
            budget_dict = {
                "Makanan": 0,
                "Transport": 0,
                "Belanja": 0,
                "Hiburan": 0,
                "Tabungan": 0,
                "Lainnya": 0
            }
        
        df = pd.DataFrame(list(budget_dict.items()), columns=["Kategori", "Anggaran"])
        # Save to CSV
        df.to_csv(budget_file, index=False)
        print(f"Budget saved to {budget_file}")  # Debug print
        return True
    except Exception as e:
        print(f"Error saving budget: {str(e)}")  # Debug print
        st.error(f"Error saving budget: {str(e)}")
        return False

# Function to get historical average spending by category
def get_historical_average_by_category(df, categories, months_back=3):
    if df.empty or "Tanggal" not in df.columns:
        return {cat: 0.0 for cat in categories}
    
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce')
    df = df.dropna(subset=["Tanggal"]) 

    df["Month"] = df["Tanggal"].dt.to_period("M")
    recent_months = sorted(df["Month"].unique())[-months_back:]

    # Filter to recent months and allowed categories
    filtered_df = df[df["Month"].isin(recent_months) & df["Kategori"].isin(categories)]

    # Group by category and compute average per month
    averages = (
        filtered_df.groupby("Kategori")["Jumlah (Rp)"]
        .mean()
        .to_dict()
    )

    return {cat: round(averages.get(cat, 0.0), 2) for cat in categories}

# Function to fetch transaction data for filtering
def fetch_data(start_date=None, end_date=None):
    if not os.path.exists(transactions_data):
        return pd.DataFrame()
    df = pd.read_csv(transactions_data)
    df = df.rename(columns={
        "Tanggal": "date",
        "Jumlah (Rp)": "amount",
        "Kategori": "category",
        "Sub-kategori": "subcategory",
        "Metode Pembayaran": "payment_method",
        "Deskripsi": "description",
        "Keterangan": "note"
    })
    df["date"] = pd.to_datetime(df["date"])
    if start_date:
        df = df[df["date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["date"] <= pd.to_datetime(end_date)]
    return df

# Function to fetch and prepare data for analysis
def fetch_data():
    try:
        # Check if file exists
        if not os.path.exists(transactions_data) or os.path.getsize(transactions_data) == 0:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=["date", "description", "amount", "category", "subcategory", "payment_method", "notes"])
        
        # Read the CSV file
        df = pd.read_csv(transactions_data)
        
        # Return empty DataFrame if no data or columns
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame(columns=["date", "description", "amount", "category", "subcategory", "payment_method", "notes"])
        
        # Rename columns to English for consistency
        df = df.rename(columns={
            "Tanggal": "date",
            "Deskripsi": "description",
            "Jumlah (Rp)": "amount",
            "Kategori": "category",
            "Sub-kategori": "subcategory",
            "Metode Pembayaran": "payment_method",
            "Catatan": "notes"
        })
        
        # Convert date column to datetime
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        
        # Drop rows with invalid dates
        df = df.dropna(subset=["date"])
        
        # Sort by date
        df = df.sort_values("date", ascending=False)
        
        return df
        
    except pd.errors.EmptyDataError:
        # Return empty DataFrame if file is empty
        return pd.DataFrame(columns=["date", "description", "amount", "category", "subcategory", "payment_method", "notes"])
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame(columns=["date", "description", "amount", "category", "subcategory", "payment_method", "notes"])

# --- Financial Summary ---
def get_financial_summary(df):
    if df.empty:
        return {
            "total_income": 0,
            "total_expense": 0,
            "balance": 0
        }
    
    total_income = df[df["category"] == "Pendapatan"]["amount"].sum()
    total_expense = df[df["category"] == "Pengeluaran"]["amount"].sum()
    balance = total_income - total_expense
    
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance
    }

# Function to load budget from CSV
def load_budget_csv():
    budget_file = os.path.join(DATA_DIR, "budget.csv")
    default_budget = {
        "Makanan": 0,
        "Transport": 0,
        "Belanja": 0,
        "Hiburan": 0,
        "Tabungan": 0,
        "Lainnya": 0
    }
    
    try:
        if os.path.exists(budget_file) and os.path.getsize(budget_file) > 0:
            df = pd.read_csv(budget_file)
            if len(df.columns) == 0:  # File exists but is empty or corrupted
                save_budget_csv(default_budget)  # Create new file with default values
                return default_budget
            return dict(zip(df["Kategori"], df["Anggaran"]))
        else:
            # Create new budget file with default values
            save_budget_csv(default_budget)
            return default_budget
    except Exception as e:
        print(f"Error loading budget: {str(e)}")  # Debug print
        st.error(f"Error loading budget: {str(e)}")
        # Return default budget values
        return {
            "Makanan": 0,
            "Transport": 0,
            "Belanja": 0,
            "Hiburan": 0,
            "Tabungan": 0,
            "Lainnya": 0
        }