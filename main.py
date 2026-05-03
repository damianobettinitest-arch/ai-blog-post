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
    
    html_cumulativo = ""

    # PASSAGGIO 1: Genera i 3 articoli uno per uno e unisce l'HTML
    for index, title in enumerate(titles):
        print(f"   -> Generazione testo (Passaggio 1): {title}")
        try:
            p1_completo = prompt1_template.replace("{titolo}", title)
            res1 = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Sei un esperto copywriter tecnico SEO."},
                    {"role": "user", "content": p1_completo}
                ]
            )
            markdown_text = res1.choices[0].message.content
            html_singolo = markdown.markdown(markdown_text)
            
            # Aggiunge separatori chiari per aiutare DeepSeek a distinguere gli articoli
            html_cumulativo += f"\n\n\n"
            html_cumulativo += f"<h1>{title}</h1>\n" # Aiuta a ribadire il titolo principale
            html_cumulativo += html_singolo
            html_cumulativo += f"\n\n"

        except Exception as e:
            print(f"      ❌ Errore su '{title}': {e}")
            # Se un articolo fallisce, continua col prossimo senza bloccare tutto

    if not html_cumulativo.strip():
        print("   ❌ Nessun HTML generato nel blocco. Salto la creazione dell'XML.")
        return False

    # PASSAGGIO 2: Invia tutto l'HTML cumulativo in UN'UNICA CHIAMATA
    print(f"   -> Conversione di gruppo in XML (Passaggio 2)...")
    try:
        p2_completo = prompt2_template.replace("{html_input}", html_cumulativo)
        res2 = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Sei un programmatore SEO esperto in esportazioni WXR XML per WordPress."},
                {"role": "user", "content": p2_completo}
            ]
        )
        xml_finale = res2.choices[0].message.content
        
        # Pulizia backticks
        xml_finale = xml_finale.replace("```xml", "").replace("```", "").strip()
        
        # Salvataggio
        nome_file = f"articoli_{data_oggi}_blocco_{batch_number}.xml"
        with open(nome_file, "w", encoding="utf-8") as f:
            f.write(xml_finale)
            
        print(f"   ✅ Blocco {batch_number} salvato con successo in: {nome_file}")
        return True

    except Exception as e:
        print(f"   ❌ Errore durante la generazione XML del blocco {batch_number}: {e}")
        return False

def main():
    if not os.path.exists("titoli.txt"):
        print("File titoli.txt non trovato.")
        return

    with open("titoli.txt", "r", encoding="utf-8") as f:
        all_titles = [line.strip() for line in f if line.strip()]

    if len(all_titles) < 1:
        print("Nessun titolo da elaborare.")
        return

    prompt1 = read_file_safe("prompt1.txt")
    prompt2 = read_file_safe("prompt2.txt")
    if not prompt1 or not prompt2: return

    if "{titolo}" not in prompt1:
        print("❌ ERRORE: Manca {titolo} in prompt1.txt!")
        return
    if "{html_input}" not in prompt2:
        print("❌ ERRORE: Manca {html_input} in prompt2.txt!")
        return

    # Dividiamo i primi 6 titoli in due blocchi da 3
    blocco1 = all_titles[0:3]
    blocco2 = all_titles[3:6]
    
    titoli_da_rimuovere = 0

    if blocco1:
        if process_batch(blocco1, prompt1, prompt2, 1):
            titoli_da_rimuovere += len(blocco1)

    if blocco2:
        if process_batch(blocco2, prompt1, prompt2, 2):
            titoli_da_rimuovere += len(blocco2)

    # Rimuoviamo da titoli.txt solo quelli processati con successo
    with open("titoli.txt", "w", encoding="utf-8") as f:
        for t in all_titles[titoli_da_rimuovere:]:
            f.write(t + "\n")

if __name__ == "__main__":
    main()
