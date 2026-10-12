# ManageQBittorrent - Documentazione

## Panoramica

`ManageQBittorrent` è un client Python per gestire qBittorrent tramite la sua API Web. Il programma si connette a un'istanza qBittorrent remota, monitora i torrent e pulisce automaticamente quelli completati e spostati.

## Funzionalità Principali

### 1. Connessione a qBittorrent
- Connessione automatica a un'istanza qBittorrent remota tramite API
- Autenticazione con username e password
- Verifica della versione dell'API e del client
- Gestione degli errori di connessione e autenticazione

### 2. Monitoraggio dei Torrent
- **Torrent Attivi**: Recupera e logga tutti i torrent in stato di download (`downloading`)
- **Report Completo**: Genera un report con il conteggio dei torrent per ogni stato (pausedUP, stalledUP, queuedUP, uploading, stoppedUP, missingFiles, ecc.)

### 3. Pulizia Automatica
Il programma identifica e rimuove automaticamente i torrent completati che soddisfano questi criteri:
- Il percorso dei file **NON** inizia con la cartella `Incomplete`
- Il percorso dei file **INIZIA** con la cartella `Downloads`
- Lo stato del torrent è uno dei seguenti:
  - `pausedUP` - In pausa dopo l'upload
  - `stalledUP` - Upload in stallo
  - `queuedUP` - In coda per l'upload
  - `uploading` - In upload
  - `stoppedUP` - Fermato dopo l'upload
  - `missingFiles` - File mancanti

I torrent vengono rimossi dalla lista qBittorrent ma **i file non vengono eliminati** dal disco.

## Configurazione

Il programma richiede un file `App/config/config.toml` con le seguenti sezioni:

### [QBittorent_Host]
Configurazione della connessione qBittorrent:
- `Host`: Indirizzo IP o hostname del server qBittorrent
- `Port`: Porta del server qBittorrent
- `username`: Nome utente per l'autenticazione
- `password`: Password per l'autenticazione

### [Path]
Percorsi per il filtraggio dei torrent:
- `Incomplete`: Percorso della cartella dei download incompleti
- `Downloads`: Percorso della cartella dei download completati

### Esempio di Configurazione
```toml
[QBittorent_Host]
Host = "192.168.1.88"
Port = 8080
username = "admin"
password = "tua_password"

[Path]
Incomplete = "/downloads/incomplete"
Downloads = "/downloads"
```

## Metodi della Classe

### `__init__()`
Inizializza il client, carica la configurazione e stabilisce la connessione a qBittorrent.

### `get_active_torrents()`
Restituisce la lista dei torrent attualmente in download.

### `log_torrents_report(torrents=None)`
Genera e logga un report con il conteggio dei torrent per ogni stato.

### `get_completed_and_moved_torrents()`
Restituisce la lista dei torrent completati e spostati che soddisfano i criteri di pulizia.

### `main()`
Esegue il flusso principale:
1. Effettua il login
2. Recupera tutti i torrent
3. Logga il report completo
4. Logga i torrent attivi
5. Identifica i torrent completati
6. Rimuove i torrent completati dalla lista
7. Effettua il logout

### `parse_config()`
Carica e valida il file di configurazione TOML.

### `initialize()`
Configura il client qBittorrent con i parametri dal file di configurazione e verifica la connessione.

## Gestione degli Errori

Il programma include una gestione robusta degli errori:
- Errori di connessione e autenticazione
- File di configurazione mancante o invalido
- Errori durante il recupero dei torrent
- Errori durante l'eliminazione dei torrent
- Tutti gli errori vengono loggati con messaggi descrittivi

## Utilizzo

Eseguire direttamente lo script:
```bash
python ManageQBittorent.py
```

Oppure importare e utilizzare la classe in altro codice:
```python
from ManageQBittorent import QBitTorrentClient

qb_client = QBitTorrentClient()
qb_client.main()
```

## Requisiti

- Python 3.x
- qbittorrentapi
- toml
- Un'istanza qBittorrent con API Web abilitata
