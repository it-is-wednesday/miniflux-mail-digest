"""
TODO:
- Use miniflux's HTML so it looks official or smth :^)
- Convert testbed to a proper test file that is still REPL-usable
- Logging
"""
import os
import smtplib
import sys
from email.message import EmailMessage
from string import Template
from typing import Iterable, TypedDict

import miniflux  # type: ignore
from bs4 import BeautifulSoup
from dotenv import load_dotenv

__version__ = "0.1"

PEEK_CHARS_COUNT = 300


def getenv(key: str) -> str:
    """Get env var or throw"""
    key = "MINIFLUX_DIGEST_" + key
    if not (val := os.getenv(key)):
        print(
            f"You need to set environment variable {key}. You can dump it in .env",
            file=sys.stderr,
        )
        sys.exit(1)
    return val


class Entry(TypedDict):
    """An entry in the digest mail message"""

    title: str
    source_feed: str
    content_peek: str
    url: str
    reading_time: int


def entry_essence(entry: dict) -> Entry:
    """
    Receive entry from Miniflux's API, extract the bits needed for HTML representation
    """
    # some feeds serve HTML in the content field rather than plaintext. can you
    # believe it?
    content_text = BeautifulSoup(entry["content"], "html.parser").text.replace("\n", " ")
    return dict(
        title=entry["title"],
        source_feed=entry["feed"]["title"],
        content_peek=f"{content_text[:PEEK_CHARS_COUNT]}…",
        url=entry["url"],
        reading_time=entry["reading_time"],
    )


def fetch_entries(client: miniflux.Client, category_title: str) -> Iterable[dict]:
    """Fetch raw entries from category"""
    try:
        category_id = next(c for c in client.get_categories() if c["title"] == category_title)["id"]
    except StopIteration:
        print(f"Uhhh what happened to the {category_title} category?", file=sys.stderr)
        sys.exit(1)

    # limit=999 because it seems like the category parameter doesn't actually work.
    # the default limit is 100 and it's hijacked by entries from other categories
    entries = client.get_entries(status="unread", category=category_id, limit=999)["entries"]
    for entry in entries:
        # idk why it leaks but it leaks haha
        if entry["feed"]["category"]["id"] == category_id:
            yield entry
    client.mark_category_entries_as_read(category_id)


def make_html(entries: list[Entry]):
    """Bake a nice HTML-based E-mail featuring _entries_"""
    with (
        open("templates/message.html", encoding="utf-8") as messagefile,
        open("templates/entry.html", encoding="utf-8") as entryfile,
    ):
        template_message = Template(messagefile.read())
        template_entry = Template(entryfile.read())
        entries_html = "".join(template_entry.substitute(**e) for e in entries)
        return template_message.substitute(entries=entries_html)


def make_mail(title: str, content: str, from_addr: str, to_addr: str) -> EmailMessage:
    """Carefully craft an Email Message"""
    msg = EmailMessage()
    msg.set_content(content)
    msg.set_type("text/html")
    msg.add_header("From", from_addr)
    msg.add_header("To", to_addr)
    msg.add_header("Subject", title)
    return msg


def main():
    """Entry point"""
    load_dotenv()

    miniflux_api_key = getenv("API_KEY")
    miniflux_api_url = getenv("API_URL")
    miniflux_category = getenv("CATEGORY_TITLE")
    smtp_password = getenv("SMTP_PASSWORD")
    smtp_server = getenv("SMTP_SERVER")
    smtp_user = getenv("SMTP_USER")
    from_addr = getenv("FROM_ADDR")
    to_addr = getenv("TO_ADDR")
    mail_title = getenv("MAIL_TITLE")

    miniflux_client = miniflux.Client(miniflux_api_url, api_key=miniflux_api_key)
    entries = map(entry_essence, fetch_entries(miniflux_client, miniflux_category))

    smtpclient = smtplib.SMTP_SSL(host=smtp_server, port=465)
    smtpclient.login(user=smtp_user, password=smtp_password)

    content = make_html(entries)
    smtpclient.send_message(make_mail(mail_title, content, from_addr, to_addr))


if __name__ == "__main__":
    main()

# Local Variables:
# pyvenv-activate: "~/.virtualenvs/miniflux-mail-digest"
# End:
