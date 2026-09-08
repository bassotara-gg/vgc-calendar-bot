# VGC Calendar Bot 🇮🇹

Bot Discord per raccogliere i messaggi del webhook Pokedata relativi a:
- League Cup VG
- League Challenge VG

e mostrarli in un calendario Discord.

## Regioni iniziali

- Toscana
- Umbria
- Lazio

Le regioni si cambiano dalla variabile `ALLOWED_REGIONS`.

## Installazione locale

Richiede Python 3.11+.

```bash
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Crea un file `.env` partendo da `.env.example`.

Per il test locale, puoi impostare le variabili d'ambiente prima di avviare:

```powershell
$env:DISCORD_TOKEN="..."
$env:EVENT_CHANNEL_ID="123456789"
$env:CALENDAR_CHANNEL_ID="987654321"
$env:ALLOWED_REGIONS="Toscana,Umbria,Lazio"
python bot.py
```

## Permessi Discord

Il bot deve poter:
- vedere il canale Pokedata;
- leggere la cronologia messaggi;
- leggere il contenuto dei messaggi;
- vedere/scrivere nel canale calendario;
- inviare messaggi;
- incorporare link.

Nel Developer Portal va attivato anche **Message Content Intent**.

## Import iniziale

La prima versione è progettata per imparare gli eventi dai messaggi Pokedata che il bot può leggere.

Se il canale contiene già molti eventi, dopo l'avvio il bot può essere esteso con un comando di import storico che scorre la cronologia. Questa funzione è volutamente separata dal parser live per poterla testare senza duplicare dati.

## GitHub

Il file `.github/workflows/bot.yml` non viene usato per mantenere il bot 24/7: GitHub Actions è adatto a test/build/deploy, non a mantenere una connessione Discord permanente.

Per eseguire il bot gratis 24/7, usare una macchina sempre accesa oppure un servizio cloud che permetta un processo persistente. Il repository GitHub può comunque rimanere la sorgente del progetto.

## Nota sul webhook

Il bot non deve essere il webhook Pokedata. Pokedata continua a pubblicare nel canale esistente; il bot legge quei messaggi.

Il bot deve quindi avere accesso al canale dove arrivano i messaggi anche se il bot "appare" o viene usato principalmente in un altro canale.


## Comando di importazione storico

Dopo aver avviato il bot, usa `/vgc_import`.
Il bot legge tutta la cronologia accessibile del canale Pokedata configurato,
estrae Cup/Challenge e conserva solo Toscana, Umbria e Lazio (o le regioni
impostate in `ALLOWED_REGIONS`).

Il bot deve avere **View Channel**, **Read Message History** e **Read Message Content**
sul canale Pokedata.


## Partecipazione
Aprendo un evento dal calendario si può scegliere 🟢 Partecipo, 🟡 Forse o 🔴 Non partecipo. La risposta è modificabile e viene salvata nel database. `👥 Chi partecipa?` mostra gli elenchi.
