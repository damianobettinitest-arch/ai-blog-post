import os
import json
import base64
import requests
import markdown
import re
from openai import OpenAI
# Le librerie Google sono commentate per ora
# from google.oauth2 import service_account
# from google.auth.transport.requests import Request

# Configurazione Secrets
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
WP_URL = os.getenv("WP_URL").rstrip('/')
WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
WP_AUTHOR_ID = os.getenv("WP_AUTHOR_ID")

# Inizializza client DeepSeek
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

def read_file_safe(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Errore: Il file {filename} non è stato trovato.")
        return None

def first_pass(title, prompt_template):
    print(f"   -> Avvio Passaggio 1 (Generazione testo per: {title})...")
    prompt_completo = prompt_template.replace("{titolo}", title)
    
    response = client.chat.completions.create(
        model="deepseek-chat", 
        messages=[
            {"role": "system", "content": "Sei un esperto copywriter tecnico SEO."},
            {"role": "user", "content": prompt_completo}
        ],
        stream=False
    )
    return response.choices[0].message.content

def second_pass(html_content, prompt2_template):
    print(f"   -> Avvio Passaggio 2 (Revisione e Conversione XML)...")
    prompt_completo = prompt2_template.replace("{html_input}", html_content)
    
    response = client.chat.completions.create(
        model="deepseek-chat", 
        messages=[
            {"role": "system", "content": "Sei un programmatore SEO esperto in XML."},
            {"role": "user", "content": prompt_completo}
        ],
        stream=False
    )
    return response.choices[0].message.content

def extract_from_xml(xml_string):
    # FILTRO ANTI-CHIACCHIERE: Cerca solo quello che sta dentro i backtick del codice
    xml_match = re.search(r'
http://googleusercontent.com/immersive_entry_chip/0

Applica queste due sostituzioni e rilancia il workflow. Vedrai che ora Python saprà scartare i "convenevoli" di DeepSeek e invierà correttamente l'ID numerico a WordPress!

    
    # 1. Isola il blocco <item> (l'articolo vero e proprio) per ignorare l'intestazione del sito
    item_match = re.search(r'<item>(.*?)</item>', xml_clean, re.DOTALL | re.IGNORECASE)
    if not item_match:
        print("\n--- 🚨 ERRORE: TAG <item> NON TROVATO 🚨 ---")
        print(xml_clean[:1000])
        raise ValueError("Non ho trovato il blocco dell'articolo nell'XML WXR.")
    
    item_block = item_match.group(1)

    # 2. Estrai Titolo, Contenuto e Descrizione (gestendo anche i CDATA del tuo prompt)
    titolo = re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', item_block, re.DOTALL | re.IGNORECASE)
    contenuto = re.search(r'<content:encoded>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</content:encoded>', item_block, re.DOTALL | re.IGNORECASE)
    metadesc = re.search(r'<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>', item_block, re.DOTALL | re.IGNORECASE)
    
    if not titolo or not contenuto:
        print("\n--- 🚨 ERRORE: TAG INTERNI NON TROVATI 🚨 ---")
        print(item_block[:1000])
        raise ValueError("Non sono riuscito a trovare i tag <title> o <content:encoded>.")
        
    final_title = titolo.group(1).strip()
    final_content = contenuto.group(1).strip()
    final_metadesc = metadesc.group(1).strip() if metadesc else ""
    
    # In base al tuo prompt, l'AIOSEO Title è esattamente uguale al titolo riformulato dell'articolo
    final_seotitle = final_title 
        
    return final_title, final_content, final_seotitle, final_metadesc

def post_to_wordpress(title, final_html, seo_title, meta_desc):
    print(f"   -> Pubblicazione su WordPress in corso...")
    endpoint = f"{WP_URL}/wp-json/wp/v2/posts"
    
    # Preparazione dell'autenticazione
    credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
    token = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json"
    }
    
    # --- MODIFICA 1: Gestione Autore (Integer) ---
    # Se il Secret WP_AUTHOR_ID non è impostato o non è un numero, usa l'ID 1 (Admin)
    author_id = 1 
    if WP_AUTHOR_ID and str(WP_AUTHOR_ID).strip().isdigit():
        author_id = int(str(WP_AUTHOR_ID).strip())
    
    # --- MODIFICA 2: Campi per AIOSEO ---
    payload = {
        "title": title,
        "content": final_html,
        "status": "publish",
        "author": author_id,
        "meta": {
            "_aioseop_title": seo_title,
            "_aioseop_description": meta_desc
        }
    }
    
    res = requests.post(endpoint, headers=headers, json=payload)
    
    if res.status_code == 201:
        post_url = res.json().get('link')
        print(f"   ✅ Articolo pubblicato con successo: {post_url}")
        return post_url
    else:
        print(f"   ❌ Errore WordPress: {res.status_code} - {res.text}")
        return None



# FUNZIONE GOOGLE COMMENTATA
# def notify_google_indexing(url):
#     ... (codice Google disattivato)

def main():
    if not os.path.exists("titoli.txt"):
        print("File titoli.txt non trovato.")
        return

    with open("titoli.txt", "r", encoding="utf-8") as f:
        all_titles = [line.strip() for line in f if line.strip()]

    if not all_titles:
        print("Lista titoli vuota.")
        return

    prompt1 = read_file_safe("prompt1.txt")
    prompt2 = read_file_safe("prompt2.txt")
    
    if not prompt1 or not prompt2:
        return

    to_process = all_titles[:6]
    remaining = all_titles[6:]

    for title in to_process:
        print(f"\n=====================================")
        print(f"Inizio elaborazione: {title}")
        try:
            # 1. Genera Markdown iniziale
            markdown_text = first_pass(title, prompt1)
            
            # 2. Converti in HTML
            html_intermedio = markdown.markdown(markdown_text)
            
            # 3. Passa HTML al secondo prompt per generare XML
            xml_text = second_pass(html_intermedio, prompt2)
            
            # 4. Estrai i dati dall'XML
            final_title, final_content, seo_title, meta_desc = extract_from_xml(xml_text)
            
            # 5. Pubblica su WP
            post_url = post_to_wordpress(final_title, final_content, seo_title, meta_desc)
            
            # INDICIZZAZIONE GOOGLE DISATTIVATA
            # if post_url:
            #     notify_google_indexing(post_url)
                
        except Exception as e:
            print(f"Errore critico su '{title}': {e}")

    # Aggiorna la lista dei titoli
    with open("titoli.txt", "w", encoding="utf-8") as f:
        for t in remaining:
            f.write(t + "\n")

if __name__ == "__main__":
    main()
