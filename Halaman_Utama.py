import streamlit as st

# Page config
st.set_page_config(page_title="Personal Finance Assistance", page_icon="📝", layout="centered")

# Title and intro
st.title('📝 Personal Finance Assistance')
st.write("""
Selamat datang di Personal Finance Assistance! 
         Aplikasi ini dirancang untuk membantu Anda mengelola keuangan pribadi dengan lebih baik.
         Anda dapat memasukkan transaksi, mengatur anggaran, dan menganalisis keuangan Anda dengan mudah.
""")

st.write("Silakan pilih salah satu opsi di menu samping untuk memulai atau klik tombol di bawah ini:")

st.markdown("###")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚀 Yuk Mulai Menghemat!"):
        st.switch_page("pages/1_Input_Transaksi.py") 
