import os
import base64
import requests
import markdown
from openai import OpenAI

# Configurazione dalle variabili d'ambiente (GitHub Secrets)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
WP_URL = os.getenv("WP_URL").rstrip('/')
WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

# Inizializza client DeepSeek (usa endpoint compatibile OpenAI)
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

def generate_article(title):
    # 1. Legge il prompt dal file esterno in modo sicuro
    try:
        with open("prompt.txt", "r", encoding="utf-8") as f:
            base_prompt = f.read()
    except FileNotFoundError:
        print("Errore: Il file prompt.txt non è stato trovato.")
        return ""

    # 2. Sostituisce la stringa {titolo} con il titolo effettivo usando .replace() 
    # (molto più sicuro degli f-string se il tuo prompt contiene altre parentesi graffe)
    prompt_completo = base_prompt.replace("{titolo}", title)
    
    # 3. Chiama DeepSeek
    response = client.chat.completions.create(
        model="deepseek-chat", 
        messages=[
            {"role": "system", "content": "Sei un esperto copywriter tecnico SEO."},
            {"role": "user", "content": prompt_completo}
        ],
        stream=False
    )
    return response.choices[0].message.content

def post_to_wordpress(title, html_content):
    endpoint = f"{WP_URL}/wp-json/wp/v2/posts"
    
    # Autenticazione Basic (User + Application Password)
    credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
    token = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "title": title,
        "content": html_content,
        "status": "publish" # Imposta 'draft' se vuoi revisionarli prima
    }
    
    res = requests.post(endpoint, headers=headers, json=payload)
    if res.status_code == 201:
        print(f"✅ Articolo '{title}' pubblicato!")
    else:
        print(f"❌ Errore per '{title}': {res.text}")

def main():
    # 1. Leggi i titoli dal file
    if not os.path.exists("titoli.txt"):
        print("File titoli.txt non trovato.")
        return

    with open("titoli.txt", "r", encoding="utf-8") as f:
        all_titles = [line.strip() for line in f if line.strip()]

    if not all_titles:
        print("Lista titoli vuota.")
        return

    # 2. Prendi i primi 6 e tieni i restanti
    to_process = all_titles[:6]
    remaining = all_titles[6:]

    # 3. Ciclo di generazione e pubblicazione
    for title in to_process:
        print(f"Elaborazione: {title}...")
        try:
            # Genera Markdown da DeepSeek
            markdown_content = generate_article(title)
            
            # Converte Markdown in HTML pulito
            html_content = markdown.markdown(markdown_content)
            
            # Pubblica su WP
            post_to_wordpress(title, html_content)
        except Exception as e:
            print(f"Errore critico su {title}: {e}")

    # 4. Aggiorna il file titoli.txt rimuovendo quelli usati
    with open("titoli.txt", "w", encoding="utf-8") as f:
        for t in remaining:
            f.write(t + "\n")

if __name__ == "__main__":
    main()
