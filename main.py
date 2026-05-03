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
    # Rimuove eventuali backtick ```xml
    xml_string = re.sub(r'```(xml)?', '', xml_string).strip()
    
    # Estrazione dei tag
    titolo = re.search(r'<titolo>(.*?)</titolo>', xml_string, re.DOTALL | re.IGNORECASE)
    contenuto = re.search(r'<contenuto>(.*?)</contenuto>', xml_string, re.DOTALL | re.IGNORECASE)
    seotitle = re.search(r'<seotitle>(.*?)</seotitle>', xml_string, re.DOTALL | re.IGNORECASE)
    metadesc = re.search(r'<metadesc>(.*?)</metadesc>', xml_string, re.DOTALL | re.IGNORECASE)
    
    if not titolo or not contenuto:
        raise ValueError("Non sono riuscito a trovare i tag <titolo> e <contenuto> nell'XML.")
        
    val_seotitle = seotitle.group(1).strip() if seotitle else ""
    val_metadesc = metadesc.group(1).strip() if metadesc else ""
        
    return titolo.group(1).strip(), contenuto.group(1).strip(), val_seotitle, val_metadesc

def post_to_wordpress(title, final_html, seo_title, meta_desc):
    print(f"   -> Pubblicazione su WordPress in corso...")
    endpoint = f"{WP_URL}/wp-json/wp/v2/posts"
    credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
    token = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json"
    }
    
    # NOTA: Qui uso "rank_math_title". Se usi Yoast, cambialo in "_yoast_wpseo_title" ecc come spiegato prima
    payload = {
        "title": title,
        "content": final_html,
        "status": "publish",
        "meta": {
            "rank_math_title": seo_title,
            "rank_math_description": meta_desc
        }
    }
    
    res = requests.post(endpoint, headers=headers, json=payload)
    if res.status_code == 201:
        post_url = res.json().get('link')
        print(f"   ✅ Articolo pubblicato: {post_url}")
        return post_url
    else:
        print(f"   ❌ Errore WP: {res.text}")
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
