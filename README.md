# MoveVideo

Applicazione Python per la gestione di video, integrazione con qBittorrent e Stash, rilevamento duplicati e generazione di feed RSS.

## Descrizione

**MoveVideo** è un insieme di script Python progettati per:
- Spostare file video da una directory sorgente a una destinazione
- Gestire duplicati basati su phash/oshash
- Integrare con qBittorrent per la gestione dei torrent
- Integrare con Stash (media server) per il metadata scraping
- Generare feed RSS automatici

Il progetto è stato strutturato come package Python ufficiale (`App/`) per una migliore portabilità e manutenibilità.

## Prerequisiti

### Software richiesto

- Python 3.12 o superiore
- `pip install -r requirements.txt`

### Configurazione

Il progetto richiede un file di configurazione `config/config.toml` con la seguente struttura:

## Installazione

1. Clona o copia il repository nella tua directory di lavoro
2. Crea un ambiente virtuale (facoltativo ma consigliato):
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   . venv/bin/activate  # Linux/macOS
   ```
3. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
4. Crea il file `config/config.toml` con le impostazioni del tuo setup
5. Verifica che qBittorrent e Stash siano raggiungibili dalle loro rispettive host/port

## Utilizzo

### Esecuzione principale

L'applicazione può essere eseguita dalla root del progetto:

```bash
python -m App.MoveVideo
```

Oppure direttamente dalla cartella `App/`:
```bash
python App/MoveVideo.py
```

### Comandi disponibili

L'applicazione supporta diversi comandi tramite argomenti da riga di comando (vedere i singoli file per i dettagli):

- **MoveVideo**: `move_files`, `delete_small_directories`, `is_video_file`
- **ManageStash**: scan, delete_duplicates_scenes, process_files, garbage collection
- **StashCli**: matching, scraping, update operations
- **ProxiedScraper**: scraping periodico, generazione RSS

### Esempio di base

Per avviare il movimento dei file video:
```bash
python -m App.MoveVideo
```

Per eseguire una scansione completa su Stash:
```bash
python -m App.ManageStash --scan
```

## Struttura del progetto

```
MoveVideo/
├── README.md          # Questo file
├── requirements.txt   # Dipendenze Python
├── config/            # Cartella di configurazione
│   └── config.toml    # Configurazione qBittorrent/Stash
├── App/               # Package Python principale
│   ├── __init__.py    # Package initialization
│   ├── Config.py      # Gestione configurazione e override environment
│   ├── Log.py         # Utility di logging personalizzata
│   ├── Types.py       # Dataclass e costanti condivise
│   ├── FindBestFile.py# Logica selezione file duplicati
│   ├── MoveVideo.py   # Spostamento file e pulizia directory
│   ├── ManageQBittorent.py  # Client qBittorrent
│   ├── ManageStash.py # Integrazione Stash
│   ├── StashCli.py    # CLI per operazioni Stash
│   ├── ProxiedScraper.py  # Web scraper + server RSS
│   └── Test.py        # Script di test/esecuzione
├── tests/             # Test unitari (nuovo)
│   └── test_findbestfile.py
└── Dockerfile         # Configurazione Docker (se presente)
```

## Configurazione avanzata

### Environment Variables

Le variabili d'ambiente possono sovrascrivere i valori del `config.toml`:

- `QBITTORENT_USERNAME`
- `QBITTORENT_PASSWORD`
- `STASH_API_KEY`
- `STASH_HOST` (formato: `http://host:port`)

### Personalizzazione

- Aggiungi nuovi proxy scraper in `ProxiedScraper.py`
- Modifica le costanti `MATCHES_STASHBOX` in `App/Types.py`
- Estendi la logica di selezione file in `App/FindBestFile.py`

## Note e limitazioni

- L'applicazione è stata testata con qBittorrent e Stash in ambiente domestico
- Alcune funzionalità richiedono che i servizi siano raggiungibili dalla macchina che esegue lo script
- Il rilevamento duplicati si basa su fingerprint (phash/oshash) presenti nei metadati di Stash
- Le directory di trash e download sono configurabili ma assume percorsi assoluti

## Licenza

Questo progetto è open source. Si prega di consultare i file di licenza eventualmente presenti.