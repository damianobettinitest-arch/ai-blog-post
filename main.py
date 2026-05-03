import os
import json
import base64
import requests
import markdown
import re
from openai import OpenAI
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# Configurazione Secrets
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
WP_URL = os.getenv("WP_URL").rstrip('/')
WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

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
    print(f"   -> Avvio Passaggio 1 (Generazione Markdown per: {title})...")
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
    # Rimuove eventuali backtick ```xml che l'IA potrebbe aggiungere all'inizio/fine
    xml_string = re.sub(r'```(xml)?', '', xml_string).strip()
    
    # Cerca i tag <titolo> e <contenuto> usando le espressioni regolari (Regex)
    # NOTA: Se il tuo prompt2 usa tag diversi (es. <title> e <body>), modificali qui sotto!
    titolo_match = re.search(r'<titolo>(.*?)</titolo>', xml_string, re.DOTALL | re.IGNORECASE)
    contenuto_match = re.search(r'<contenuto>(.*?)</contenuto>', xml_string, re.DOTALL | re.IGNORECASE)
    
    if not titolo_match or not contenuto_match:
        raise ValueError("Non sono riuscito a trovare i tag <titolo> e <contenuto> nell'XML di DeepSeek.")
        
    return titolo_match.group(1).strip(), contenuto_match.group(1).strip()

def post_to_wordpress(title, final_html):
    print(f"   -> Pubblicazione su WordPress in corso...")
    endpoint = f"{WP_URL}/wp-json/wp/v2/posts"
    credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
    token = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "title": title,
        "content": final_html,
        "status": "publish" 
    }
    
    res = requests.post(endpoint, headers=headers, json=payload)
    if res.status_code == 201:
        post_url = res.json().get('link')
        print(f"   ✅ Articolo pubblicato: {post_url}")
        return post_url
    else:
        print(f"   ❌ Errore WP: {res.text}")
        return None

def notify_google_indexing(url):
    # (Mantieni la funzione Google intatta dal codice precedente)
    gcp_json_str = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if not gcp_json_str:
        return

    try:
        gcp_info = json.loads(gcp_json_str)
        credentials = service_account.Credentials.from_service_account_info(
            gcp_info, scopes=["https://www.googleapis.com/auth/indexing"]
        )
        credentials.refresh(Request())
        token = credentials.token

        endpoint = "https://indexing.googleapis.com/v3/urlNotifications:publish"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"url": url, "type": "URL_UPDATED"}
        
        res = requests.post(endpoint, headers=headers, json=payload)
        if res.status_code == 200:
            print(f"   🚀 Inviato a Google Search Console!")
    except Exception as e:
        print(f"   ❌ Errore Google API: {e}")

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
        return # Si ferma se mancano i file dei prompt

    # Prende i primi 6 titoli per oggi
    to_process = all_titles[:6]
    remaining = all_titles[6:]

    for title in to_process:
        print(f"\n=====================================")
        print(f"Inizio elaborazione: {title}")
        try:
            # PASSAGGIO 1: Genera Markdown
            markdown_text = first_pass(title, prompt1)
            
            # Conversione Markdown -> HTML
            html_intermedio = markdown.markdown(markdown_text)
            
            # PASSAGGIO 2: Ottimizzazione e conversione in XML
            xml_text = second_pass(html_intermedio, prompt2)
            
            # ESTRAZIONE dall'XML generato
            # (Lo script cerca i tag <titolo> e <contenuto> per capire cosa inviare a WP)
            final_title, final_content = extract_from_xml(xml_text)
            
            # PUBBLICAZIONE
            post_url = post_to_wordpress(final_title, final_content)
            
            # INDICIZZAZIONE GOOGLE
            if post_url:
                notify_google_indexing(post_url)
                
        except Exception as e:
            print(f"Errore critico su '{title}': {e}")

    # Aggiorna il file titoli.txt
    with open("titoli.txt", "w", encoding="utf-8") as f:
        for t in remaining:
            f.write(t + "\n")

if __name__ == "__main__":
    main()
