import os
import json
import base64
import requests
import markdown
import re
from openai import OpenAI

# Configurazione Secrets
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
WP_URL = os.getenv("WP_URL").rstrip('/')
WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

def read_file_safe(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Errore: Il file {filename} non è stato trovato.")
        return None

def first_pass(title, prompt_template):
    # SOSTITUZIONE E VERIFICA
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
    # SOSTITUZIONE E VERIFICA
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
    xml_clean = re.sub(r'^```xml\s*', '', xml_string, flags=re.IGNORECASE)
    xml_clean = re.sub(r'```$', '', xml_clean).strip()
    
    titolo = re.search(r'<titolo>(.*?)</titolo>', xml_clean, re.DOTALL | re.IGNORECASE)
    contenuto = re.search(r'<contenuto>(.*?)</contenuto>', xml_clean, re.DOTALL | re.IGNORECASE)
    seotitle = re.search(r'<seotitle>(.*?)</seotitle>', xml_clean, re.DOTALL | re.IGNORECASE)
    metadesc = re.search(r'<metadesc>(.*?)</metadesc>', xml_clean, re.DOTALL | re.IGNORECASE)
    
    if not titolo or not contenuto:
        print("\n--- 🚨 ERRORE: TAG MANCANTI 🚨 ---")
        print("XML Generato (primi 500 car.):", xml_string[:500])
        raise ValueError("Tag <titolo> o <contenuto> non trovati.")
        
    val_seotitle = seotitle.group(1).strip() if seotitle else ""
    val_metadesc = metadesc.group(1).strip() if metadesc else ""
        
    return titolo.group(1).strip(), contenuto.group(1).strip(), val_seotitle, val_metadesc

def post_to_wordpress(title, final_html, seo_title, meta_desc):
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
        "status": "publish",
        "meta": {
            "rank_math_title": seo_title,
            "rank_math_description": meta_desc
        }
    }
    
    res = requests.post(endpoint, headers=headers, json=payload)
    if res.status_code == 201:
        return res.json().get('link')
    else:
        print(f"   ❌ Errore WP: {res.text}")
        return None

def main():
    if not os.path.exists("titoli.txt"):
        print("Nessun file titoli.txt")
        return

    # Legge i titoli evitando righe vuote
    with open("titoli.txt", "r", encoding="utf-8") as f:
        all_titles = [line.strip() for line in f if line.strip()]

    prompt1 = read_file_safe("prompt1.txt")
    prompt2 = read_file_safe("prompt2.txt")
    
    if not prompt1 or not prompt2:
        return

    # 🛑 CONTROLLI DI SICUREZZA ANTI-CLONE 🛑
    if "{titolo}" not in prompt1:
        print("❌ ERRORE CRITICO: Non hai scritto {titolo} dentro prompt1.txt! Lo script è stato bloccato per evitare cloni.")
        return
        
    if "{html_input}" not in prompt2:
        print("❌ ERRORE CRITICO: Non hai scritto {html_input} dentro prompt2.txt! Lo script è stato bloccato per evitare cloni.")
        return

    to_process = all_titles[:6]
    remaining = all_titles[6:]

    for title in to_process:
        print(f"\n=====================================")
        print(f"Elaborazione: {title}")
        try:
            markdown_text = first_pass(title, prompt1)
            html_intermedio = markdown.markdown(markdown_text)
            xml_text = second_pass(html_intermedio, prompt2)
            
            final_title, final_content, seo_title, meta_desc = extract_from_xml(xml_text)
            post_url = post_to_wordpress(final_title, final_content, seo_title, meta_desc)
            
            if post_url:
                print(f"   ✅ Pubblicato: {post_url}")
                
        except Exception as e:
            print(f"Errore su '{title}': {e}")

    with open("titoli.txt", "w", encoding="utf-8") as f:
        for t in remaining:
            f.write(t + "\n")

if __name__ == "__main__":
    main()
