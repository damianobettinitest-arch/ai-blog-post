import os
import markdown
import re
from datetime import datetime
from openai import OpenAI

# Configurazione API DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

def read_file_safe(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Errore: File {filename} non trovato.")
        return None

def clean_filename(title):
    # Rimuove caratteri non ammessi nei nomi dei file (come ?, :, /, ecc.)
    return re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')[:50]

def process_single_article(title, prompt1_template, prompt2_template):
    print(f"\n--- Elaborazione Articolo: {title} ---")
    data_oggi = datetime.now().strftime("%Y-%m-%d")
    slug_titolo = clean_filename(title)
    
    try:
        # PASSAGGIO 1: Generazione Markdown
        print("   -> Passaggio 1: Generazione testo...")
        p1_completo = prompt1_template.replace("{titolo}", title)
        res1 = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": p1_completo}]
        )
        markdown_text = res1.choices[0].message.content
        html_intermedio = markdown.markdown(markdown_text)

        # PASSAGGIO 2: Conversione in XML
        print("   -> Passaggio 2: Conversione in XML...")
        p2_completo = prompt2_template.replace("{html_input}", html_intermedio)
        res2 = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": p2_completo}]
        )
        xml_output = res2.choices[0].message.content
        
        # Pulizia backticks markdown se presenti
        xml_output = xml_output.replace("```xml", "").replace("```", "").strip()
        
        # Salvataggio file singolo
        nome_file = f"{data_oggi}_{slug_titolo}.xml"
        with open(nome_file, "w", encoding="utf-8") as f:
            f.write(xml_output)
            
        print(f"   ✅ File salvato: {nome_file}")
        return True

    except Exception as e:
        print(f"   ❌ Errore critico su '{title}': {e}")
        return False

def main():
    if not os.path.exists("titoli.txt"):
        print("File titoli.txt non trovato.")
        return

    with open("titoli.txt", "r", encoding="utf-8") as f:
        all_titles = [line.strip() for line in f if line.strip()]

    if not all_titles:
        print("Nessun titolo da elaborare.")
        return

    prompt1 = read_file_safe("prompt1.txt")
    prompt2 = read_file_safe("prompt2.txt")
    if not prompt1 or not prompt2: return

    # Prende i primi 6
    to_process = all_titles[:6]
    titoli_pubblicati = []

    for title in to_process:
        successo = process_single_article(title, prompt1, prompt2)
        if successo:
            titoli_pubblicati.append(title)

    # Aggiorna titoli.txt rimuovendo solo quelli riusciti
    nuova_lista = [t for t in all_titles if t not in titoli_pubblicati]
    with open("titoli.txt", "w", encoding="utf-8") as f:
        for t in nuova_lista:
            f.write(t + "\n")
            
    print(f"\nFine lavoro. Articoli generati oggi: {len(titoli_pubblicati)}")

if __name__ == "__main__":
    main()

