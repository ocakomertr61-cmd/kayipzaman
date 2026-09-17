import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Page Configuration
st.set_page_config(page_title="Müşteri Kayıp Zaman Takip Sistemi", layout="wide", page_icon="⏱️")

st.title("⏱️ Müşteri Kayıp Zaman & Fatura Takip Sistemi")
st.markdown("---")

# Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(ttl=0)
        return df
    except Exception:
        return pd.DataFrame(columns=[
            "Tarih", "Müşteri Adı", "Sorumlu Mühendis", "İrsaliye No", 
            "Referans No", "Seri No", "Duruş Nedeni", "İşlem Açıklaması", 
            "Miktar", "P/H", "Hesaplanan Zaman (Saat)", "Kayıp Zaman (Saat)", 
            "Son Durum", "Hata Görseli Linki", "Onay Belgesi Linki"
        ])

# Tam sizin istediğiniz seçimli 'Son Durum' opsiyonları
DURUM_OPSIYONLARI = ["Mail Atıldı", "Onay Geldi", "Red Oldu", "Revize İstendi"]

DURUS_NEDENLERI = [
    "Rework / Yeniden İşleme", 
    "Malzeme Eksikliği / Bekleme", 
    "Kalite Problemi / Ayıklama", 
    "Ekipman / Line Arızası", 
    "Kalıp / Parça Uyumsuzluğu", 
    "Diğer"
]

tab1, tab2, tab3 = st.tabs(["➕ Yeni Kayıp Zaman Kaydı Ekle", "📊 Kayıt Listesi & Durum Güncelleme", "📈 Analiz & Özet"])

# ---------------- TAB 1: FORM ----------------
with tab1:
    st.subheader("Referans Bazlı Kayıp Zaman Kayıt Formu")
    
    with st.form("kayip_zaman_formu", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            musteri_adi = st.text_input("Müşteri Adı *")
            sorumlu_muhendis = st.text_input("Müşteri Sorumlu Mühendis Adı")
            irsaliye_no = st.text_input("İrsaliye No")
            
        with col2:
            referans_no = st.text_input("Referans No *")
            seri_no = st.text_input("Seri No")
            durus_nedeni = st.selectbox("Duruş / Zaman Kaybı Nedeni *", DURUS_NEDENLERI)
            
        with col3:
            miktar = st.number_input("Miktar (Adet)", min_value=1, value=1, step=1)
            ph = st.number_input("P/H (Parça / Saat)", min_value=0.1, value=100.0, step=1.0)
            kayip_zaman_saat = st.number_input("Kayıp Zaman / Fiili Duruş (Saat) *", min_value=0.0, value=1.0, step=0.1)
            
        c_durum, c_bos = st.columns([1, 2])
        with c_durum:
            # Seçimli Son Durum
            son_durum = st.selectbox("Son Durum *", DURUM_OPSIYONLARI)
            
        islem_aciklamasi = st.text_area("İşlem Açıklaması", placeholder="Yapılan işlem, duruş gerekçesi ve detaylar...")
        
        c_link1, c_link2 = st.columns(2)
        with c_link1:
            hata_gorseli_link = st.text_input("Hata Görseli Linki (Google Drive / OneDrive vb.)")
        with c_link2:
            onay_belgesi_link = st.text_input("Gelen Onay Belgesi Linki (Google Drive / OneDrive vb.)")
            
        submit_btn = st.form_submit_button("💾 Kaydı Google Tabloya Kaydet", use_container_width=True)
        
        if submit_btn:
            if not musteri_adi or not referans_no:
                st.error("Lütfen Müşteri Adı ve Referans No alanlarını doldurunuz!")
            else:
                hesaplanan_zaman = round(miktar / ph, 2) if ph > 0 else 0.0
                bugun = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                yeni_kayit = pd.DataFrame([{
                    "Tarih": bugun,
                    "Müşteri Adı": musteri_adi,
                    "Sorumlu Mühendis": sorumlu_muhendis,
                    "İrsaliye No": irsaliye_no,
                    "Referans No": referans_no,
                    "Seri No": seri_no,
                    "Duruş Nedeni": durus_nedeni,
                    "İşlem Açıklaması": islem_aciklamasi,
                    "Miktar": miktar,
                    "P/H": ph,
                    "Hesaplanan Zaman (Saat)": hesaplanan_zaman,
                    "Kayıp Zaman (Saat)": kayip_zaman_saat,
                    "Son Durum": son_durum,
                    "Hata Görseli Linki": hata_gorseli_link,
                    "Onay Belgesi Linki": onay_belgesi_link
                }])
                
                mevcut_df = load_data()
                guncel_df = pd.concat([mevcut_df, yeni_kayit], ignore_index=True)
                
                conn.update(data=guncel_df)
                st.success(f" Referans {referans_no} başarıyla kaydedildi!")
                st.rerun()

# ---------------- TAB 2: LIST & EDIT ----------------
with tab2:
    st.subheader("Tüm Kayıtlar, Son Durum Güncelleme & Excel İndirme")
    df = load_data()
    
    if df.empty:
        st.info("Henüz kayıtlı bir veri bulunmuyor.")
    else:
        # Excel / CSV İndirme Butonu
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Tüm Kayıtları Excel / CSV Olarak İndir",
            data=csv_data,
            file_name=f"kayip_zaman_takip_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        st.markdown("---")
        
        # İnteraktif Tablo (Son Durum Hücrede Seçmeli)
        edited_df = st.data_editor(
            df,
            column_config={
                "Son Durum": st.column_config.SelectboxColumn(
                    "Son Durum",
                    help="Kaydın güncel durumunu seçin",
                    options=DURUM_OPSIYONLARI,
                    required=True,
                ),
                "Duruş Nedeni": st.column_config.SelectboxColumn(
                    "Duruş Nedeni",
                    options=DURUS_NEDENLERI,
                    required=True,
                )
            },
            num_rows="dynamic",
            use_container_width=True
        )
        
        if st.button("🔄 Değişiklikleri ve Son Durumu Kaydet"):
            conn.update(data=edited_df)
            st.success("Tablodaki güncellemeler Google Sheets'e kaydedildi!")
            st.rerun()

# ---------------- TAB 3: DASHBOARD ----------------
with tab3:
    st.subheader("Genel Durum & Analiz Panosu")
    df = load_data()
    
    if not df.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Toplam Kayıt", f"{len(df)} Adet")
        
        toplam_kayip = pd.to_numeric(df['Kayıp Zaman (Saat)'], errors='coerce').sum()
        m2.metric("Toplam Kayıp Zaman", f"{toplam_kayip:.1f} Saat")
        
        onaylanan = pd.to_numeric(df[df['Son Durum'] == "Onay Geldi"]['Kayıp Zaman (Saat)'], errors='coerce').sum()
        m3.metric("Onaylanan Süre", f"{onaylanan:.1f} Saat")
        
        bekleyen = pd.to_numeric(df[df['Son Durum'] == "Mail Atıldı"]['Kayıp Zaman (Saat)'], errors='coerce').sum()
        m4.metric("Onay Bekleyen Süre", f"{bekleyen:.1f} Saat")
        
        st.markdown("---")
        
        c_grafik1, c_grafik2 = st.columns(2)
        with c_grafik1:
            st.write("### Müşteri Bazlı Toplam Kayıp Zamanlar (Saat)")
            musteri_ozet = df.groupby('Müşteri Adı')['Kayıp Zaman (Saat)'].sum()
            st.bar_chart(musteri_ozet)
            
        with c_grafik2:
            st.write("### Duruş Nedenlerine Göre Dağılım")
            neden_ozet = df.groupby('Duruş Nedeni')['Kayıp Zaman (Saat)'].sum()
            st.bar_chart(neden_ozet)
