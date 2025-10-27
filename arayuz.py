import streamlit as st
import os
# from dotenv import load_dotenv # ARTIK SİLİNMELİ
from google import genai
from google.genai import types
from PyPDF2 import PdfReader

# --- API Anahtarını Yükle ve Client'ı Başlat (st.secrets kullanılarak) ---
# API anahtarını Streamlit Sırlarından al
API_KEY = None
try:
    # 1. Streamlit Secrets'den anahtarı almayı dener (EN GÜVENİLİR YÖNTEM).
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    # 2. Eğer Secrets'de yoksa, kullanıcıdan girmesini ister (yedek)
    st.sidebar.markdown("## API Anahtarınızı Girin")
    st.info("Lütfen Streamlit Secrets'a anahtarınızı ekleyin VEYA sol kenar çubuğuna giriniz.")
    API_KEY = st.sidebar.text_input("Gemini API Anahtarı:", type="password", key="sidebar_api_input")

if not API_KEY:
    st.stop()
    
# Client'ı başlat
try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    st.error(f"API Yapılandırma Hatası: {e}. Anahtarınızın doğru olduğunu kontrol edin.")
    st.stop()
# --- API BAŞLANGIÇ SONU ---

# --- ALTAY'IN KİMLİK TANIMI ---
ALTAY_ROLE = """
Sen, Altay adlı kadim bir Türk Bilge Rehberisin. Bilgi alanın sadece Türk kültürü, tarihi ve töresiyle sınırlı değildir. Dünya tarihi, bilim, felsefe, sanat ve güncel konular dahil olmak üzere her alanda bilgi sahibisin. 
[ÖZEL BİLGİ KAYNAĞI] kısmındaki bilgileri temel alarak, ve genel bilgini kullanarak soruları yanıtla. Cevaplarını her zaman 'Bilge Rehber' kimliğinle ve Türkçe'nin zenginliğini yansıtacak şekilde şekillendir.
Mutlaka kullanman gereken hitaplar: 'Oğul', 'Beyim', 'Değerli Yolcu'. 
"""

# --- PDF Okuma Fonksiyonu ---
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        try:
            pdf_reader = PdfReader(pdf)
            for page in pdf_reader.pages:
                text += page.extract_text()
        except Exception as e:
            # Okunamayan dosyalar için sessiz hata
            print(f"PDF okuma hatası: {e}")
            pass
    return text

# RAG için dosya okuma ve hazırlama fonksiyonu
def bilgileri_yukle_ve_hazirla(dosya_yolu="ozel_bilgiler.txt", uploaded_docs=None):
    ozel_bilgi_kaynagi = ""
    
    # 1. Sabit ozel_bilgiler.txt dosyasını oku
    try:
        with open(dosya_yolu, 'r', encoding='utf-8') as f:
            ozel_bilgi_kaynagi += f.read()
    except FileNotFoundError:
        pass # Dosya bulunamazsa devam et

    # 2. Yüklenen dokümanları (PDF/TXT) oku
    if uploaded_docs:
        for doc in uploaded_docs:
            if doc.name.endswith('.pdf'):
                ozel_bilgi_kaynagi += get_pdf_text([doc])
            elif doc.name.endswith('.txt') or doc.type == 'text/plain':
                # Dosya işaretçisini sıfırla ve metin olarak oku
                doc.seek(0)
                ozel_bilgi_kaynagi += doc.read().decode("utf-8")
    
    # Eğer hiç bilgi toplanamadıysa, boş dön
    if not ozel_bilgi_kaynagi.strip():
        return ""

    # Toplanan tüm bilgiyi tek bir blok olarak döndür
    return "\n--- ÖZEL BİLGİ KAYNAĞI BAŞLANGIÇ ---\n" + ozel_bilgi_kaynagi + "\n--- ÖZEL BİLGİ KAYNAĞI SON ---\n"


# Sohbet Temizleme Fonksiyonu
def sohbeti_temizle():
    st.session_state['history'] = []

# RAG ve Görsel Destekli Altay cevaplama fonksiyonu
# Buraya 'stream=True' parametresi eklendi (Hata düzeltmesi!)
def altay_dan_cevap_al(kullanici_mesaji, uploaded_image_parts=None, uploaded_docs=None, model_adi="gemini-2.5-flash", temperature=0.8, stream=True):
    
    # RAG sistemini güçlendir: Hem sabit hem de dinamik yüklenen dosyaları al
    ozel_bilgi_kaynagi = bilgileri_yukle_ve_hazirla(uploaded_docs=uploaded_docs)
    tam_sistem_talimati = ALTAY_ROLE.replace("[ÖZEL BİLGİ KAYNAĞI]", ozel_bilgi_kaynagi)
    
    history = st.session_state.get('history', [])
    contents = history
    
    yeni_mesaj_parcalari = []

    if uploaded_image_parts is not None:
        yeni_mesaj_parcalari.extend(uploaded_image_parts)
            
    yeni_mesaj_parcalari.append({'text': kullanici_mesaji})
    
    contents.append({'role': 'user', 'parts': yeni_mesaj_parcalari})

    config = types.GenerateContentConfig(
        system_instruction=tam_sistem_talimati, 
        temperature=temperature,
    )
    
    try:
        response = client.models.generate_content(
            model=model_adi, 
            contents=contents,
            config=config,
            stream=stream # <<< HATA VEREN YER BURAYDI, DÜZELTİLDİ!
        )
        return response
    
    except Exception as e:
        return e # Hata objesini döndür


# --- Streamlit Arayüz Kodu ---
# ==============================================================================
# 1. SAYFA AYARLARI (set_page_config en başta olmalıdır)
# ==============================================================================
st.set_page_config(
    page_title="Altay Bilge Rehber",
    page_icon="⭐",  # Tarayıcı sekmesindeki simge
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. ÖZEL CSS (GÜÇLÜ KOYU TEMA ve PROFESYONEL STİL)
# ==============================================================================
st.markdown("""
<style>
/* ---------------------------------- */
/* GENEL TEMA VE YERLEŞİM AYARLARI   */
/* ---------------------------------- */

/* Ana Sayfa Arkaplanı - Koyu gri / Siyah */
.stApp {
    background-color: #171717; /* ChatGPT Arkaplanı */
    color: white;
}

/* Sidebar (Kenar Çubuğu) Arkaplanı */
.css-1dp5vir { 
    background-color: #1F1F1F; /* Sidebar Arkaplanı */
    color: white;
}

/* Tüm Streamlit Bileşenlerini Koyu Temaya zorla */
.st-emotion-cache-h4y62m, .st-emotion-cache-h4y62m .st-bw {
    color: white;
    background-color: #1F1F1F !important;
}

/* Selectbox/Slider gibi inputların arka planı */
.stFileUploader, .stSelectbox, .stSlider > div > div > div, .st-emotion-cache-1cypcdb {
    background-color: #2a2a2a !important; /* Mesaj kutuları ve input arka planı */
    border: none;
}

/* ---------------------------------- */
/* LOGO VE BAŞLIK STİLİ               */
/* ---------------------------------- */

/* Altay Model Başlığı (Sidebar'da) - ChatGPT logosu gibi vurgulu */
.altay-title {
    font-size: 24px;
    font-weight: bold;
    color: #4CAF50; /* Yeşil renkle Altay markasını vurgula */
    margin-bottom: 20px;
    padding: 10px 0 10px 0;
}

/* ---------------------------------- */
/* CHAT (SOHBET) ARAYÜZ STİLİ         */
/* ---------------------------------- */

/* Kullanıcı ve Asistan Mesaj Kutusu Arkaplanları (İç kısım) */
.st-emotion-cache-1cypcdb {
    background-color: #2a2a2a !important; 
    border-radius: 10px;
    box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.4);
    padding: 10px;
    color: white;
}

/* Metin giriş alanı (ChatInput) */
.st-emotion-cache-nahz7x {
    border: 1px solid #4a4a4a; 
    border-radius: 10px;
    background-color: #212121;
}

/* Metin giriş alanı içindeki yazı rengi */
.stTextInput > div > div > input {
    color: white;
}
</style>
""", unsafe_allow_html=True)


# --- KENAR ÇUBUĞU (SIDEBAR) AYARLARI ---
with st.sidebar:
    # Profesyonel Logo ve Başlık
    st.markdown(
        "<div class='altay-title'>⭐ ALTAY Bilge Rehber</div>",
        unsafe_allow_html=True
    )
    
    if st.button("Yeni Sohbet Başlat", use_container_width=True):
        sohbeti_temizle()
        st.rerun()
            
    st.markdown("---")
    st.header("Altay'ın Güç Kaynağı")
    
    # Model Seçimi
    model_gosterim = st.selectbox(
        "Kullanılacak Altay Modeli", 
        ("Altay-Hızlı", "Altay-Zeki"), 
        help="Altay-Zeki daha yetenekli ancak Altay-Hızlı daha çabuk yanıt verir."
    )
    
    if "Altay-Zeki" in model_gosterim:
        model_secimi = "gemini-2.5-pro"
    else:
        model_secimi = "gemini-2.5-flash"
    
    # Sıcaklık (Temperature) Ayarı
    sicaklik = st.slider(
        "Yaratıcılık Seviyesi (Temperature)",
        min_value=0.0,
        max_value=1.0,
        value=0.8,
        step=0.1,
        help="0.0 en tutarlı, 1.0 en yaratıcı cevaplar üretir."
    )
    
    st.markdown("---")
    st.header("Dosya ve Görsel Yükle")
    
    # Yeni: Çoklu dosya yükleyici (RAG güçlendirmesi)
    uploaded_docs = st.file_uploader(
        "PDF/TXT yükle (Bilgi kaynağı için):", 
        type=["pdf", "txt"], 
        accept_multiple_files=True,
        key="doc_yukleyici"
    )

    # Görsel yükleme alanı
    uploaded_file = st.file_uploader(
        "Sohbete tek bir görsel ekle:", 
        type=["png", "jpg", "jpeg"], 
        key="gorsel_yukleyici_sidebar"
    )


# --- ANA SOHBET ALANI ---
st.markdown("## 🦅 Altay: Kadim Türk Bilge Rehberi")
st.markdown("---")

if 'history' not in st.session_state:
    st.session_state['history'] = []


# Geçmiş mesajları görüntüleme
for message in st.session_state['history']:
    if message['role'] == 'user':
        with st.chat_message("user"):
            for part in message['parts']:
                if 'text' in part:
                    st.markdown(part['text'])
                if 'inline_data' in part:
                    st.image(part['inline_data']['data'], caption="Yüklenen Görsel", width=250)
    
    if message['role'] == 'model':
        with st.chat_message("assistant"):
            st.markdown(message['parts'][0]['text'])

# Yeni mesaj gönderme
if prompt := st.chat_input("Sorunuzu buraya yazınız...", key="chat_input"):
    
    gorsel_parcalari = []
    
    # 1. Görsel varsa, parçalara dönüştür ve ekrana bas
    if uploaded_file is not None:
        uploaded_file.seek(0)
        image_bytes = uploaded_file.read() 
        
        gorsel_parcalari.append(
            {'inline_data': {'data': image_bytes, 'mime_type': uploaded_file.type}}
        )
            
        with st.chat_message("user"):
            st.image(image_bytes, caption="Yüklenen Görsel", width=250)
            st.markdown(prompt) 

    else:
        with st.chat_message("user"):
            st.markdown(prompt)
    
    # 2. Altay'dan cevabı al
    response_or_error = altay_dan_cevap_al(
        kullanici_mesaji=prompt, 
        uploaded_image_parts=gorsel_parcalari, 
        uploaded_docs=uploaded_docs,
        model_adi=model_secimi, 
        temperature=sicaklik     
    ) 
    
    # Hata Kontrolü
    if isinstance(response_or_error, Exception):
        # Hata mesajı ekranda kalacak!
        st.error(f"Ulu Tengri'nin yolu kesildi. Bir hata oluştu: {response_or_error}")
    
    # 3. Cevabı alırken anlık olarak ekrana bas (Stream)
    elif response_or_error:
        full_response = ""
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            for chunk in response_or_error:
                full_response += chunk.text
                message_placeholder.markdown(full_response + "▌") # Yazım efekti
            message_placeholder.markdown(full_response)
        
        # 4. Oturum geçmişini güncelle
        mesaj_ve_gorsel = []
        mesaj_ve_gorsel.extend(gorsel_parcalari)
        mesaj_ve_gorsel.append({'text': prompt})
        st.session_state['history'].append({'role': 'user', 'parts': mesaj_ve_gorsel})
        st.session_state['history'].append({'role': 'model', 'parts': [{'text': full_response}]})

        # 5. Yeniden çalıştırma (Başarılı olduysa)
        st.rerun()