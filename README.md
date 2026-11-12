# Sito web di CriticalPrep

Sito statico bilingue (italiano/inglese) del prodotto **CriticalPrep**: home, prezzi, download,
guide, novità, supporto con FAQ, privacy, termini d'uso e rimborsi. È pensato per essere pubblicato
gratis su **Cloudflare Pages** (consigliato) o **GitHub Pages** con un dominio proprio.

- Nessun cookie, nessun tracciamento, nessuna risorsa da CDN di terze parti (font di sistema).
- Tema chiaro e scuro automatico (segue le impostazioni del sistema), adatto al telefono, accessibile
  (link "salta al contenuto", contrasti AA, focus visibile, `lang` e `hreflang` corretti).
- La radice `/` reindirizza a `/it/` o `/en/` in base alla lingua del browser (italiano come ripiego).

## Perché un piccolo generatore e non HTML scritto a mano

Il sito ha 2 lingue × 11 pagine che condividono intestazione, menu, piè di pagina e molti valori
(dominio, email, prezzo, dati del titolare). Scrivendo l'HTML a mano ogni modifica andrebbe ripetuta
in 22 file. Un generatore come Hugo o Eleventy risolverebbe, ma aggiunge un'installazione e una
toolchain da mantenere.

La via di mezzo è `build.py`: **un solo file Python, senza dipendenze** (basta il `python3` già
presente su macOS con gli strumenti di Xcode e nelle immagini di build di Cloudflare e GitHub). Prende
un layout, i contenuti e `config.json` e scrive HTML puro in `public/`. Il risultato è statico al 100%:
si può anche pubblicare la cartella `public/` così com'è.

## Struttura

```
website/
├── build.py                 generatore (python3 build.py)
├── config.json              ★ UNICO punto per dominio, email, prezzi, link, titolare
├── templates/
│   ├── layout.html          layout di tutte le pagine
│   ├── root.html            pagina radice che sceglie la lingua
│   └── 404.html
├── content/
│   ├── strings.json         testi dell'interfaccia (menu, piè di pagina...) in it/en
│   ├── faq.json             domande frequenti (pagina Supporto)
│   ├── changelog.json       novità per versione (pagina Novità)
│   ├── it/*.html            pagine italiane       ┐ stessa `key` nella front matter
│   ├── en/*.html            pagine inglesi        ┘ = stessa pagina nelle due lingue
│   ├── it/guides/*.html     guide italiane (elencate in automatico)
│   └── en/guides/*.html     guide inglesi
├── static/                  copiato così com'è in public/
│   ├── css/site.css
│   ├── img/icon.svg         icona segnaposto
│   ├── appcast.xml          feed Sparkle (vuoto, con istruzioni)
│   ├── _headers             intestazioni di sicurezza per Cloudflare Pages
│   ├── CNAME                dominio per GitHub Pages
│   ├── .nojekyll            per GitHub Pages
│   └── robots.txt
└── public/                  risultato generato (non versionato)
```

Ogni pagina comincia con una piccola *front matter*:

```html
---
key: pricing          # identificativo comune alle due lingue (serve al selettore di lingua)
slug: prezzi          # percorso: /it/prezzi/
title: Prezzi
description: Testo per i motori di ricerca.
---
```

Nei contenuti si usano `{{c.chiave}}` (valori di `config.json`), `{{t.chiave}}` (testi di
`strings.json`), `{{u.key}}` (URL di una pagina nella stessa lingua, es. `{{u.refunds}}`) e
`{{{blocco}}}` per i blocchi generati (`faq_list`, `guides_list`, `changelog_list`). Una variabile
sconosciuta interrompe la build con un errore, così un link rotto non arriva online.

### Aggiungere contenuti senza toccare il layout

- **Una guida:** crea `content/it/guides/nome.html` e `content/en/guides/nome.html` con la stessa
  `key` (es. `guide-discord`) e `slug: guide/...` / `slug: guides/...`; facoltativo `order: 30`.
  Compare da sola nella pagina Guide. La build avvisa se manca la traduzione.
- **Una FAQ:** aggiungi un elemento a `content/faq.json` (id, domanda e risposta in it/en).
- **Una versione:** aggiungi una voce in cima a `content/changelog.json` e un `<item>` in
  `static/appcast.xml` (le istruzioni sono nei commenti del file).
- **Una pagina nuova:** crea i due file in `content/it/` e `content/en/`; per metterla nel menu
  aggiungi la sua `key` a `nav_order` o `footer_order` e un testo `nav_<key>` in `strings.json`.
- **Gli screenshot:** metti le immagini in `static/img/screens/` e sostituisci nei file `home.html`
  i blocchi `<div class="shot-frame">` con `<img src="/img/screens/...png" alt="...">` (c'è un
  commento `SEGNAPOSTO` / `PLACEHOLDER` accanto a ciascuno).

## Provarlo in locale

```bash
cd website
```

```bash
python3 build.py --serve
```

Apri <http://localhost:8000>. Dopo ogni modifica interrompi con Ctrl+C e rilancia. Per una porta
diversa: `PORT=8080 python3 build.py --serve`. Senza `--serve` genera soltanto `public/`.

`python3 build.py` stampa l'elenco dei segnaposto ancora da compilare; `python3 build.py --strict`
fallisce finché ne resta qualcuno: usalo come comando di build quando il sito sarà definitivo.

Nelle pagine i segnaposto `[tra parentesi quadre]` sono evidenziati in giallo, e i riquadri
**«Da verificare con un legale / commercialista»** segnalano le parti da far controllare.
Entrambi vanno eliminati prima della pubblicazione definitiva (i riquadri sono i `<div class="legal-check">`).

## Pubblicare su Cloudflare Pages (consigliato)

Funziona anche con un repository **privato** ed è gratuito.

1. Crea un account Cloudflare e aggiungi il dominio (vedi sotto).
2. *Workers & Pages › Create › Pages › Connect to Git* e scegli il repository.
3. Impostazioni di build:
   - **Root directory:** `website` (oppure lascia vuoto se usi un repository dedicato al sito con i file in radice)
   - **Build command:** `python3 build.py` (poi `python3 build.py --strict` quando non ci sono più segnaposto)
   - **Build output directory:** `public`
4. *Save and Deploy*. Ogni push sul ramo principale ripubblica il sito; i rami ottengono un'anteprima.
5. *Custom domains › Set up a custom domain*: aggiungi `criticalprep.app` e `www.criticalprep.app`.

`static/_headers` imposta già le intestazioni di sicurezza (CSP restrittiva, niente iframe, ecc.).

> Se preferisci non dare a Cloudflare l'accesso al repository dell'app, usa un repository solo per il
> sito (vedi sotto) oppure pubblica a mano: `npx wrangler pages deploy public --project-name criticalprep`.

## Pubblicare su GitHub Pages

GitHub Pages gratuito richiede un **repository pubblico**. Il repository dell'app deve restare privato,
quindi la proposta è un **repository separato solo per il sito**, ad esempio `criticalprep-website`:

1. Crea il repository pubblico e copia dentro il **contenuto** di questa cartella `website/`
   (i file vanno in radice: `build.py`, `config.json`, `content/`, ...).
2. Crea `.github/workflows/pages.yml`:

   ```yaml
   name: Pubblica il sito
   on:
     push:
       branches: [main]
     workflow_dispatch:
   permissions:
     contents: read
     pages: write
     id-token: write
   concurrency:
     group: pages
     cancel-in-progress: true
   jobs:
     deploy:
       runs-on: ubuntu-latest
       environment:
         name: github-pages
         url: ${{ steps.deployment.outputs.page_url }}
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: "3.12"
         - run: python3 build.py
         - uses: actions/upload-pages-artifact@v3
           with:
             path: public
         - id: deployment
           uses: actions/deploy-pages@v4
   ```

3. Nel repository: *Settings › Pages › Source: GitHub Actions*.
4. *Settings › Pages › Custom domain*: `criticalprep.app`, poi spunta *Enforce HTTPS*.
   Il file `CNAME` viene già generato da `config.json`.

GitHub Pages ignora `_headers` (niente intestazioni di sicurezza personalizzate): un motivo in più
per preferire Cloudflare Pages. La pagina `404.html` funziona su entrambi.

Per tenere sincronizzato il repository del sito con questa cartella si può usare, dal repository
dell'app: `git subtree push --prefix website <remote-del-sito> main`.

## Dominio, sottodomini ed email

Consiglio di gestire il DNS su Cloudflare (gratis) anche se il dominio è registrato altrove:
acquista il dominio (anche direttamente su *Cloudflare Registrar*, a prezzo di costo) oppure, se
l'hai preso da un altro registrar, aggiungilo a Cloudflare e cambia i *nameserver* presso il registrar
con quelli che Cloudflare ti indica.

Record DNS da impostare (in *DNS › Records*):

| Nome | Tipo | Valore | Note |
|---|---|---|---|
| `criticalprep.app` (`@`) | — | creato da Cloudflare Pages quando aggiungi il dominio personalizzato | con GitHub Pages: 4 record `A` verso `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153` |
| `www` | CNAME | `criticalprep.pages.dev` (o `<utente>.github.io`) | poi una *Redirect Rule* `www` → dominio principale |
| `ai` | dipende dall'hosting del proxy | Cloudflare Workers: *Custom domain* `ai.criticalprep.app` nel Worker (il record si crea da solo); Fly.io/VPS: `CNAME`/`A` indicato dal fornitore | il proxy AI dell'abbonamento |
| `MX` e `TXT` | — | creati da *Email Routing* | per l'inoltro email |

Futuri download e aggiornamenti: il feed Sparkle è già su `https://criticalprep.app/appcast.xml`;
i DMG possono restare su GitHub Releases oppure, più avanti, andare su un sottodominio
`download.criticalprep.app` (ad esempio un bucket Cloudflare R2 pubblico).

### Email gratuita con Cloudflare Email Routing

1. *Email › Email Routing › Get started*: Cloudflare aggiunge da solo i record `MX` e `TXT` (SPF).
2. Aggiungi l'indirizzo di destinazione (la tua casella personale) e confermalo dal link ricevuto.
3. *Routing rules*: crea `supporto@criticalprep.app` → la tua casella. Facoltativi:
   `privacy@`, `support@` (comodo per gli utenti inglesi) o una regola *catch-all*.
4. Per **rispondere** dall'indirizzo del dominio, Email Routing non basta (inoltra soltanto):
   - in Gmail: *Impostazioni › Account › Invia messaggi come* con un servizio SMTP (es. Brevo o
     Resend, piano gratuito) e aggiungi al record SPF l'`include:` del servizio scelto;
   - oppure una casella vera (Zoho Mail free, iCloud+ con dominio personalizzato, Fastmail...).

Lo stesso indirizzo va indicato su Lemon Squeezy come email di supporto del negozio.

## Segnaposto da compilare prima della registrazione su Lemon Squeezy

Lemon Squeezy controlla che il sito mostri prodotto, prezzi, contatti, privacy, termini e politica di
rimborso. Prima di inviare la richiesta di attivazione del negozio:

**In `config.json`** (`python3 build.py` li elenca tutti):

| Chiave | Cosa inserire |
|---|---|
| `domain`, `site_url`, `ai_proxy_host` | dominio definitivo (ora `criticalprep.app`) |
| `support_email`, `privacy_email` | indirizzi definitivi (ora `supporto@criticalprep.app`) |
| `owner_name`, `owner_address`, `owner_vat` | nome o ragione sociale, indirizzo, partita IVA del titolare |
| `governing_law`, `court` | legge applicabile e foro competente (con il legale) |
| `price_monthly`, `price_note` | prezzo e nota IVA, nelle due lingue, uguali a quelli configurati su Lemon Squeezy |
| `monthly_allowance` | descrizione comprensibile del consumo mensile incluso |
| `checkout_url` | link di checkout della variante su Lemon Squeezy (*Products › Share*) |
| `customer_portal_url` | URL del portale clienti del negozio (es. `https://<negozio>.lemonsqueezy.com/billing`) |
| `refund_window_days` | giorni per il rimborso del primo acquisto |
| `ai_provider`, `ai_provider_privacy_url` | fornitore AI usato dal proxy e link alla sua informativa |
| `hosting_provider`, `hosting_region` | hosting del proxy AI e regione dei server |
| `app_version`, `min_macos`, `dmg_size` | versione, macOS minimo e dimensione del DMG |
| `download_url`, `releases_url` | link a GitHub Releases (utente e repository) |
| `legal_last_updated` | data delle pagine legali nelle due lingue |

**Nei testi delle pagine** (cerca `[` in `content/`):

- `privacy.html`: durata di conservazione dello storico consumi `[N mesi]` e delle email di supporto `[24 mesi]`;
- `refunds.html`: regola sul consumo massimo per il rimborso `[es. meno del 20%]` e scelta sulla rinuncia al recesso;
- `home.html`: i quattro segnaposto degli screenshot;
- `static/img/icon.svg`: icona definitiva dell'app.

**Da verificare** (i riquadri «Da verificare con un legale/commercialista»):

- **GDPR** (privacy): titolare, basi giuridiche, tempi di conservazione, DPA con fornitore AI e
  hosting, trasferimenti extra-UE, ruolo del Game Master rispetto alle voci registrate su Discord;
- **diritto di recesso** (rimborsi) e sua rinuncia per i servizi digitali, coerente con le impostazioni di Lemon Squeezy;
- **termini d'uso**: clausole per i consumatori, sospensione della licenza, legge e foro;
- **fiscale** (prezzi): IVA e regime fiscale dei ricavi da Lemon Squeezy;
- **dati del titolare** nel piè di pagina e nelle pagine legali.

**Da allineare con l'app** (quando il negozio sarà attivo): le etichette citate in FAQ e guide
(*Impostazioni › AI › Abbonamento*, *Attiva*, *Disattiva questo Mac*, l'indicatore di consumo)
devono corrispondere a quelle reali dell'app; la pagina Download dice che l'app è firmata e
autenticata (notarized) da Apple: verificarlo prima della pubblicazione.
