# flask-app-template

A personal Flask application template for home-network Docker deployments. This repo serves as the base layer for all Flask-based tools, pulled at build time into each app's Docker image.

\---

## Design Philosophy

This template is intentionally thin. It provides infrastructure, routing conventions, and a consistent UI shell — nothing app-specific. Apps built on this template should only need to add their own page templates, handlers, and requirements. **Backwards compatibility is a priority** — changes to this template should not break existing apps built on it.

\---

## Architecture Overview

### How the Template Is Used

Each app has its own repo. That app's `Dockerfile` clones this template repo at build time, then layers app-specific files on top. App files override template files where names conflict.

```
Build sequence:
1. Start from python:3.11-slim
2. Clone flask-app-template from GitHub (always latest main)
3. Install template base requirements
4. Install app-specific requirements
5. COPY template files into /app
6. COPY app-specific files into /app (overrides template where needed)
```

The app repo structure:

```
appname/
├── app/                        ← app-specific files
│   ├── templates/
│   │   └── my\_tool.html        ← new tool page(s)
│   ├── page\_handlers.py        ← app-specific handlers
│   ├── db.py                   ← if persistence needed
│   └── requirements.txt        ← app-specific packages
├── Dockerfile                  ← layered build (see pattern below)
├── docker-compose.yml          ← app-specific compose
├── Makefile                    ← app-specific makefile
└── .env.example                ← documents app-specific vars
```

### What Lives Where

|Location|Contents|Rationale|
|-|-|-|
|App repo → container|Templates, static files, Python code|Versioned, deployed via git pull + restart|
|NAS `/Docker/appname/`|logs, server\_files, database files|Persistent, private, survives container rebuild|
|NAS `/config/appname/.env`|All environment variables|Survives hardware failure, kept off GitHub|

### NAS Override for Development

During active development, you can mount a local NAS path over the container's `/app/templates` to enable live template editing without rebuilds. This is optional and not the default. See Development Workflow below.

\---

## Template File Structure

```
flask-app-template/
├── README.md
├── requirements.txt            ← base packages (Flask, anthropic, gunicorn, etc.)
├── app.py                      ← generic routing, error handlers
├── config.py                   ← Flask app factory, logging, Claude client setup
├── page\_handlers.py            ← handle\_claude\_call\_page, handle\_no\_call\_page
├── utils.py                    ← shared utilities
├── file\_processors.py          ← file upload handling, validation
├── binary\_file\_handler.py      ← serving binary files from server\_files
└── templates/
    ├── base.html               ← Bootstrap + Children's Hospital theme, nav
    ├── home.html               ← landing page (app name/description injected)
    ├── 404.html
    └── 500.html
```

Static files (CSS tweaks, shared JS) live in `static/` and are also included in the template. App-specific static files go in `app/static/`.

### The `new-app-starter/` Folder

The template repo includes a `new-app-starter/` folder that serves as the canonical starting point for every new app. Copy its contents into your new app repo and follow the substitution instructions below.

```
new-app-starter/
├── Dockerfile                  ← layered build pattern, ready to use
├── docker-compose.yml          ← NFS volumes, env\_file path, port config
├── Makefile                    ← all standard targets, NAS bootstrap logic
├── .env.example                ← standard variables + placeholder for app-specific
└── app/
    ├── requirements.txt        ← empty, ready for app-specific packages
    ├── page\_handlers.py        ← stub handler with comments explaining the pattern
    └── templates/
        └── example\_tool.html   ← functional minimal example: form → Claude → result
```

**After copying `new-app-starter/` to a new repo, find and replace these placeholders:**

|Placeholder|Replace with|Appears in|
|-|-|-|
|`APP\_NAME=myapp`|Your app name, lowercase, hyphens ok|Makefile, docker-compose.yml, .env.example|
|`myapp\_logs`|`{appname}\_logs`|docker-compose.yml|
|`myapp\_server\_files`|`{appname}\_server\_files`|docker-compose.yml|
|`:/Docker/myapp/`|`:/Docker/{appname}/`|docker-compose.yml|
|`container\_name: myapp`|`container\_name: {appname}`|docker-compose.yml|
|`myapp-network`|`{appname}-network`|docker-compose.yml|

Claude will handle these substitutions automatically when starting a new project — see "When Starting with Claude" below.

\---

## Environment Variables

### The Bootstrap Problem

`NAS\_IP` and `NAS\_MOUNT\_PATH` must be known before the NAS is mounted, so they cannot come from a `.env` on the NAS. These two variables are hardcoded as defaults in the Makefile and can be overridden at the command line:

```bash
make up NAS\_IP=192.168.0.200
```

Everything else comes from the `.env` file on the NAS.

### Standard `.env` Structure

All apps use this base structure. App-specific variables are added below the standard block.

```bash
# ── Infrastructure ─────────────────────────────────────────────
NAS\_IP=192.168.0.134
NAS\_MOUNT\_PATH=/mnt/nas
HOST\_PORT=5000
APP\_NAME=myapp

# ── Flask ──────────────────────────────────────────────────────
SECRET\_KEY=                    # auto-generated by make setup
FLASK\_ENV=production
FLASK\_DEBUG=false

# ── API Keys ──────────────────────────────────────────────────
CLAUDE\_API\_KEY=

# ── App-Specific ───────────────────────────────────────────────
# Add app-specific variables here
```

### Where `.env` Lives

The `.env` file lives on the NAS at:

```
NAS:/config/{APP\_NAME}/.env
```

It is **never committed to any repo**. Each app repo contains only `.env.example` for documentation.

\---

## NAS Volume Convention

NFS volumes follow this naming and path convention:

```yaml
volumes:
  appname\_logs:
    driver\_opts:
      type: nfs
      device: ":/Docker/appname/logs"
      o: nfsvers=4,addr=${NAS\_IP},nolock,soft,rw
  appname\_server\_files:
    driver\_opts:
      type: nfs
      device: ":/Docker/appname/server\_files"
      o: nfsvers=4,addr=${NAS\_IP},nolock,soft,rw
```

Standard volumes for all apps: `logs`, `server\_files`. Add `database` for apps with SQLite persistence.

\---

## App Dockerfile Pattern

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update \&\& apt-get install -y gcc curl git \\
    \&\& rm -rf /var/lib/apt/lists/\*

# Pull template from GitHub at build time
ARG TEMPLATE\_REF=main
RUN git clone --depth 1 --branch ${TEMPLATE\_REF} \\
    https://github.com/kylebrothers/flask-app-template /tmp/template

# Install template base requirements
RUN pip install --no-cache-dir -r /tmp/template/requirements.txt

# Install app-specific requirements
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy template layer
RUN cp -r /tmp/template/. .

# Copy app layer (overrides template where needed)
COPY app/ .

# Create directories
RUN mkdir -p logs server\_files

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:5000/health || exit 1

CMD \["python", "app.py"]
```

To pin to a specific template version:

```bash
docker-compose build --build-arg TEMPLATE\_REF=v1.0
```

\---

## Makefile Conventions

All apps share these standard targets:

|Target|Description|
|-|-|
|`make help`|Show available commands|
|`make setup`|Check deps, mount NAS, verify .env exists|
|`make build`|Build Docker image|
|`make up`|Setup + build + start container|
|`make down`|Stop container|
|`make restart`|Down + up|
|`make logs`|Tail container logs|
|`make shell`|Bash shell inside container|
|`make clean`|Remove containers and images|
|`make status`|Show container status|
|`make pull`|Git pull + restart (standard deployment command)|
|`make dev`|Start with FLASK\_DEBUG=true|

### Self-Bootstrapping Deployment

The Makefile handles all first-time setup on a fresh Debian server:

1. Checks for `nfs-common` and installs if missing (requires sudo)
2. Creates mount point and mounts NAS if not already mounted (requires sudo)
3. Verifies `.env` exists on NAS at expected path
4. Builds and starts container

A complete new-server deployment from a bare Debian install with Docker:

```bash
sudo apt install docker.io docker-compose
git clone https://github.com/kylebrothers/appname
cd appname
make up
```

`nfs-common` installation is handled by `make up` automatically.

\---

## Adding a New Page to an App

1. Create `app/templates/my\_tool.html` extending `base.html`
2. Add handler logic to `app/page\_handlers.py` if needed
3. No changes to `app.py` required — generic routing picks up any new template automatically
4. Add any new packages to `app/requirements.txt`
5. `make restart` to rebuild and deploy

The URL for a new template `my\_tool.html` is automatically `/my-tool`.

\---

## Page Types

The generic routing system supports two page types, declared in the template's hidden form field:

|Type|Description|
|-|-|
|`claude-call`|Sends form data to Claude API, returns generated content|
|`no-call`|Processes form data server-side without Claude API|

\---

## Development Workflow

### Standard (recommended)

1. Edit files via VS Code Remote-SSH connected to server
2. Files live in the git repo on the server
3. Commit and push via VS Code Git panel
4. `make restart` to rebuild container with latest changes

### Live Template Editing (optional, development only)

Mount a NAS path over the container's template directory in `docker-compose.yml`:

```yaml
volumes:
  - /mnt/nas/dev/templates:/app/templates
```

Remove this mount before committing `docker-compose.yml`.

\---

## Starting a New App

1. Create a new GitHub repo and clone it to your server
2. Copy the contents of `new-app-starter/` from this repo into the new repo
3. Find and replace all placeholders (see `new-app-starter/` section above)
4. Create `NAS:/config/{APP\_NAME}/.env` from `.env.example`
5. Create NAS directories: `NAS:/Docker/{APP\_NAME}/logs`, `NAS:/Docker/{APP\_NAME}/server\_files`
6. Add app-specific files to `app/`
7. Commit and push
8. `make up`

### When Starting with Claude

Share the following with a new Claude project:

* This README
* The new (mostly empty) app repo
* Any relevant data files or context for the app

Claude will:

* Handle all placeholder substitutions in the starter files
* Produce only app-specific files: page templates, handlers, db.py, requirements additions
* Not modify template files unless a specific override is needed for the app
* Follow the patterns established in `new-app-starter/example\_tool.html` for new pages

\---

## Backwards Compatibility Policy

Changes to this template should:

* Not rename or remove existing files without a major version bump
* Not change function signatures in `page\_handlers.py`, `utils.py`, or `config.py`
* Not change the `base.html` block structure (`{% block content %}`, `{% block scripts %}`)
* Add new features as optional, with sensible defaults

Breaking changes should be tagged with a new version (e.g. `v2.0`) so apps can pin to the previous version via `TEMPLATE\_REF`.

