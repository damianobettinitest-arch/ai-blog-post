import os
import markdown
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

def process_batch(titles, prompt1_template, prompt2_template, batch_number):
    print(f"\n--- Inizio Elaborazione Blocco {batch_number} ({len(titles)} titoli) ---")
    data_oggi = datetime.now().strftime("%Y-%m-%d")
    accumulatore_xml = ""

    for title in titles:
        print(f"   -> Elaborazione: {title}")
        try:
            # PASSAGGIO 1: Generazione Markdown
            p1_completo = prompt1_template.replace("{titolo}", title)
            res1 = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": p1_completo}]
            )
            markdown_text = res1.choices[0].message.content

            # CONVERSIONE: Markdown -> HTML
            html_intermedio = markdown.markdown(markdown_text)

            # PASSAGGIO 2: HTML -> XML Speciale (Prompt 2)
            p2_completo = prompt2_template.replace("{html_input}", html_intermedio)
            res2 = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": p2_completo}]
            )
            xml_articolo = res2.choices[0].message.content
            
            # Pulizia opzionale: rimuove i tag di formattazione markdown che l'IA mette a volte intorno all'XML
            xml_articolo = xml_articolo.replace("```xml", "").replace("```", "").strip()
            
            accumulatore_xml += xml_articolo + "\n\n"

        except Exception as e:
            print(f"      ❌ Errore su '{title}': {e}")

    # Salva il file del blocco
    nome_file = f"articoli_{data_oggi}_blocco_{batch_number}.xml"
    with open(nome_file, "w", encoding="utf-8") as f:
        f.write(accumulatore_xml)
    
    print(f"✅ Blocco {batch_number} salvato in: {nome_file}")
    return True

def main():
    if not os.path.exists("titoli.txt"):
        print("File titoli.txt non trovato.")
        return

    # Legge i titoli
    with open("titoli.txt", "r", encoding="utf-8") as f:
        all_titles = [line.strip() for line in f if line.strip()]

    if len(all_titles) < 1:
        print("Nessun titolo da elaborare.")
        return

    prompt1 = read_file_safe("prompt1.txt")
    prompt2 = read_file_safe("prompt2.txt")
    if not prompt1 or not prompt2: return

    # DIVISIONE IN 3 + 3
    blocco1 = all_titles[0:3]
    blocco2 = all_titles[3:6]
    
    titoli_rimossi = 0

    # Elabora primo blocco
    if blocco1:
        if process_batch(blocco1, prompt1, prompt2, 1):
            titoli_rimossi += len(blocco1)

    # Elabora secondo blocco
    if blocco2:
        if process_batch(blocco2, prompt1, prompt2, 2):
            titoli_rimossi += len(blocco2)

    # Aggiorna titoli.txt rimuovendo solo quelli effettivamente processati (massimo 6)
    with open("titoli.txt", "w", encoding="utf-8") as f:
        for t in all_titles[titoli_rimossi:]:
            f.write(t + "\n")

if __name__ == "__main__":
    main()
    
