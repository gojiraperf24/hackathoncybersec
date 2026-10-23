\# civic-ingest



Data ingestion layer for a civic grievance intelligence platform.



This module pulls publicly accessible posts from social media and RSS feeds,

redacts personally identifiable information (PII), deduplicates records, and

stores them in PostgreSQL so later modules (classification, clustering,

dashboard) can consume them.



Current status



&#x20;Connector  Status  Requirement 

\---------

&#x20;RSS (Reddit, forums, news)  ✅ Working  None 

&#x20;YouTube  ⏸ Ready, needs key  Free YouTube Data API v3 key 

&#x20;X (Twitter)  ⏸ Ready, needs key  Paid X API tier 



\---



\## 1. Prerequisites



Install these before anything else



\- Python 3.10 – 3.14 — \[python.org](httpswww.python.orgdownloads)

&#x20; (During install, tick Add Python to PATH.)

\- Git — \[git-scm.com](httpsgit-scm.com)

\- Docker Desktop — \[docker.comproductsdocker-desktop](httpswww.docker.comproductsdocker-desktop)

&#x20; After installing, launch Docker Desktop and wait for the whale icon in the

&#x20; system tray. The engine must be running before you start the containers.



&#x20;Windows users use Command Prompt (cmd), not PowerShell, for the

&#x20;commands below. The activation and file-copy syntax differs between the two.



\---



\## 2. First-time setup



```cmd

&#x20;1. Clone the repo

git clone httpsgithub.comYOUR-USERNAMEcivic-ingest.git

cd civic-ingest



&#x20;2. Create and activate a virtual environment

python -m venv .venv

.venvScriptsactivate.bat



&#x20;3. Install dependencies

pip install -r requirements.txt



&#x20;4. Download the spaCy language model (used by PII redaction)

python -m spacy download en\_core\_web\_lg



&#x20;5. Create your environment file from the template

copy .env.example .env

```



Now open `.env` in a text editor and fill in the values. At minimum, keep

the `DATABASE\_URL` and S3 block exactly as shown — they match the Docker

containers you are about to start.



```env

DATABASE\_URL=postgresql+psycopgciviccivic@localhost5432civic



\# Leave these blank until you have real keys (see section 6)

X\_BEARER\_TOKEN=

YOUTUBE\_API\_KEY=



S3\_ENDPOINT=httplocalhost9000

S3\_ACCESS\_KEY=minio

S3\_SECRET\_KEY=minio123

S3\_BUCKET=civic-media

S3\_REGION=us-east-1



MAX\_MEDIA\_BYTES=52428800

```



&#x20;⚠️ Never commit `.env`. It holds secrets. It is already listed in

&#x20;`.gitignore`. Only `.env.example` (with blank values) belongs in the repo.



\---



\## 3. Start the database and object storage



Make sure Docker Desktop is running, then from the project root



```cmd

docker compose up -d

```



This starts two containers



\- `postgres` — the database, on `localhost5432`

\- `minio` — S3-compatible storage for media, on `localhost9000`

&#x20; (web console at `httplocalhost9001`, login `minio`  `minio123`)



Wait \~15 seconds for Postgres to finish initialising. Check both are healthy



```cmd

docker ps

```



You should see both containers with status `Up`.



To stop them later



```cmd

docker compose down

```



(Add `-v` to also delete the stored data. Omit `-v` unless you want a

clean slate.)



\---



\## 4. Run one ingestion cycle



```cmd

python -m src.runner

```



Expected output ends with a line like



```

cycle\_complete dup=0 error=3 new=25

```



\- `new` — rows newly inserted

\- `dup` — items skipped because they were already seen in this run

\- `error` — connectors that failed (usually missing API keys — see section 6)



&#x20;Running it again will fetch the newest posts. Because each item's ID includes

&#x20;the platform and native post ID, previously ingested posts are not duplicated.



\---



\## 5. Query the database



The `source\_items` table holds every ingested record.



Count rows per platform



```cmd

docker exec -it civic-ingest-postgres-1 psql -U civic -d civic -c select platform, count() from source\_items group by platform;

```



Look at the five most recent records



```cmd

docker exec -it civic-ingest-postgres-1 psql -U civic -d civic -c select native\_id, left(text, 60) as snippet, timestamp from source\_items order by timestamp desc limit 5;

```



Open an interactive SQL shell (useful for longer queries)



```cmd

docker exec -it civic-ingest-postgres-1 psql -U civic -d civic

```



Inside the shell, type SQL directly (no `-c`, no backslashes)



```sql

select platform, count() from source\_items group by platform;

```



Type `q` and press Enter to exit.



&#x20;Windows note every `docker exec ... psql ...` command must be on a

&#x20;single line. The `` line-continuation character used in LinuxmacOS

&#x20;does not work in `cmd`.



\---



\## 6. Adding real API keys



\### YouTube (free)



1\. Go to \[console.cloud.google.com](httpsconsole.cloud.google.com)

2\. Create a project, then enable YouTube Data API v3

3\. Create an API key under APIs \& Services → Credentials

4\. Paste it into `.env` as `YOUTUBE\_API\_KEY=...`

5\. Re-run `python -m src.runner`



Free quota is 10,000 unitsday — enough for development.



\### X  Twitter (paid)



The recent-search endpoint used by `srcconnectorsx\_connector.py` requires a

paid X API tier. Until you have one, leave `X\_BEARER\_TOKEN` blank; the

connector will log an error and the rest of the pipeline will continue.



\### RSS (no key)



Edit `configsources.yaml` and replace the example feeds with real ones



```yaml

rss

&#x20; feeds

&#x20;   - name reddit-india

&#x20;     url httpswww.reddit.comrindianew.rss

&#x20;   - name reddit-bangalore

&#x20;     url httpswww.reddit.comrbangalorenew.rss

&#x20; poll\_interval\_sec 600

```



Any public RSS feed works — subreddits, local news civic sections, forums.



\---



\## 7. Project layout



```

civic-ingest

├── .env.example          # template — copy to .env and fill in

├── .gitignore            # excludes .env, .venv, \_\_pycache\_\_, etc.

├── docker-compose.yml    # Postgres + MinIO

├── requirements.txt

├── config

│   └── sources.yaml      # feeds, keywords, search queries

├── src

│   ├── config.py         # typed settings loaded from .env

│   ├── models.py         # RawItem schema + SQLAlchemy table

│   ├── runner.py         # orchestrates one ingestion cycle

│   ├── connectors

│   │   ├── base.py       # abstract BaseConnector

│   │   ├── x\_connector.py

│   │   ├── youtube\_connector.py

│   │   └── rss\_connector.py

│   └── pipeline

│       ├── dedupe.py     # content-hash deduplication

│       ├── media.py      # image download + perceptual hash

│       ├── pii.py        # Presidio-based redaction

│       └── persist.py    # insert into Postgres

└── tests

&#x20;   └── test\_dedupe.py

```



\---



\## 8. Contributing



\### Reporting a bug



Open an issue with



\- What you ran (the exact command)

\- The full error output (copy-paste, not a screenshot)

\- Your OS and `python --version`



\### Submitting a pull request



1\. Fork the repository (button top-right on GitHub)

2\. Clone your fork

&#x20;  ```cmd

&#x20;  git clone httpsgithub.comYOUR-USERNAMEcivic-ingest.git

&#x20;  cd civic-ingest

&#x20;  ```

3\. Create a branch with a descriptive name

&#x20;  ```cmd

&#x20;  git checkout -b featureyoutube-pagination

&#x20;  ```

4\. Make your changes. If you touch ingestion logic, add a test under

&#x20;  `tests`.

5\. Run the tests

&#x20;  ```cmd

&#x20;  python -m pytest tests

&#x20;  ```

6\. Commit and push

&#x20;  ```cmd

&#x20;  git add .

&#x20;  git commit -m Add pagination to YouTube connector

&#x20;  git push origin featureyoutube-pagination

&#x20;  ```

7\. Open a pull request on GitHub from your branch into `main`. Describe

&#x20;  what you changed and why.



Guidelines



\- One logical change per PR — don't mix a bugfix with a refactor.

\- Match the existing code style (type hints, `structlog` for logging).

\- Never commit `.env`, secrets, or generated data.

\- If you add a new connector, subclass `BaseConnector` and emit `RawItem`

&#x20; objects; the runner picks it up from `configsources.yaml`.



\---



\## 9. Troubleshooting



&#x20;Symptom  Cause  fix 

\------

&#x20;`'docker' is not recognized`  Docker Desktop is not installed or not running. Install it, launch it, open a new terminal, then retry. 

&#x20;`docker compose up` fails pulling `miniominio`  The official MinIO image was withdrawn. Use `pgstysilolatest` or `cgr.devchainguardminiolatest` in `docker-compose.yml`. 

&#x20;`ValidationError ... int\_parsing`  A value in `.env` has a typo (e.g. a trailing letter). Check the field named in the error. 

&#x20;`ModuleNotFoundError No module named 'src'`  You are not in the project root. `cd` into the folder that contains `src`. 

&#x20;`connection refused` when running the runner  Postgres container isn't ready. Wait 15–20 s after `docker compose up`, or check `docker ps`. 

&#x20;`ImportError cannot import name ...`  A file contains the wrong content (often a copy-paste mix-up between `models.py` and `connectorsbase.py`). Delete `\_\_pycache\_\_` folders after fixing. 

&#x20;`401 UNAUTHORIZED`  `400 Bad Request` in logs  API key missing or invalid. Expected until you add real keys (section 6). 



\---



\## 10. Roadmap



\- \[x] RSS ingestion with PII redaction and deduplication

\- \[x] PostgreSQL persistence

\- \[X] Persistent dedupe (unique index + `IntegrityError` handling)

\- \[ ] YouTube connector with pagination

\- \[ ] X connector (paid tier)

\- \[ ] Media upload to MinIO

\- \[ ] NLP classification module (grievance category, sentiment, urgency)

\- \[ ] Computer vision module (pothole  garbage  waterlogging detection)

\- \[ ] Clustering and priority scoring

\- \[ ] Monitoring dashboard



