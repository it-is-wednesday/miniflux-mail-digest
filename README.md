# Miniflux mail digest
Gathers unread entries from a category of your choice and lumps them into an
intelligible mess of an email

## Configuration
You'll need to set the following env vars (or dump them in a `.env` file):

```
MINIFLUX_DIGEST_API_KEY=
MINIFLUX_DIGEST_API_URL=
MINIFLUX_DIGEST_SMTP_PASSWORD=
MINIFLUX_DIGEST_SMTP_SERVER=
MINIFLUX_DIGEST_SMTP_USER=
MINIFLUX_DIGEST_FROM_ADDR=
MINIFLUX_DIGEST_TO_ADDR=
MINIFLUX_DIGEST_MAIL_TITLE=
```

## Installation
``` shell
scripts/make-venv
.venv/bin/pip install .
```

## Usage
``` shell
.venv/bin/miniflux-digest
```

It'll work
