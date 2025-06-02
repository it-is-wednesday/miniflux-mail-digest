"""
Miniflux digest.

Fetch unread Miniflux entries, compile an E-mail digest out of them, mark them
as read — and send it to its way to waste my time!
"""

import os
import pkgutil
import smtplib
import sys
import urllib.parse
from dataclasses import asdict, dataclass
from email.message import EmailMessage
from string import Template
from typing import Iterable, List

import miniflux  # type: ignore
from bs4 import BeautifulSoup
from dotenv import load_dotenv

__version__ = "0.1"

PEEK_CHARS_COUNT = 300


def main() -> None:
    """Entry point."""
    load_dotenv()

    miniflux_api_key = getenv("API_KEY")
    miniflux_api_url = strip_version_from_url(getenv("API_URL"))
    smtp_password = getenv("SMTP_PASSWORD")
    smtp_server = getenv("SMTP_SERVER")
    smtp_user = getenv("SMTP_USER")
    from_addr = getenv("FROM_ADDR")
    to_addr = getenv("TO_ADDR")
    mail_title = getenv("MAIL_TITLE")

    miniflux_client = miniflux.Client(miniflux_api_url, api_key=miniflux_api_key)
    entries = map(entry_essence, fetch_entries(miniflux_client))

    smtpclient = smtplib.SMTP_SSL(host=smtp_server, port=465)
    smtpclient.login(user=smtp_user, password=smtp_password)

    content = make_html(entries)
    smtpclient.send_message(make_mail(mail_title, content, from_addr, to_addr))


def getenv(key: str) -> str:
    """Get env var or exit(1)."""
    key = f"MINIFLUX_DIGEST_{key}"
    val = os.getenv(key)
    if not val:
        print(
            f"You need to set environment variable {key}. You can dump it in .env",
            file=sys.stderr,
        )
        sys.exit(1)
    return val


def strip_version_from_url(url: str) -> str:
    """
    >>> strip_url_path("https://kaki.com/miniflux/v1")
    https://kaki.com/miniflux
    """
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.replace("/v1", "")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


@dataclass
class Entry:
    """
    An entry in the digest mail message.

    This is an internal representation, not to be confused with EntryResponse —
    which is what gets yielded by the Miniflux API.
    """

    title: str
    source_feed: str
    content_peek: str
    url: str
    reading_time: int


def entry_essence(entry: dict) -> Entry:
    """Receive entry from Miniflux's API, extract the bits needed for HTML representation."""
    # some feeds serve HTML in the content field rather than plaintext. can you
    # believe it?
    content_text = BeautifulSoup(entry["content"], "html.parser").text.replace("\n", " ")
    return Entry(
        title=entry["title"],
        source_feed=entry["feed"]["title"],
        content_peek=f"{content_text[:PEEK_CHARS_COUNT]}…",
        url=entry["url"],
        reading_time=entry["reading_time"],
    )


def fetch_entries(client: miniflux.Client) -> Iterable[dict]:
    """Fetch raw unread entries, mark all as read."""
    entries = client.get_entries(status="unread")["entries"]
    yield from entries

    # mark all encountered feeds read
    for feed_id in {entry["feed"]["id"] for entry in entries}:
        client.mark_feed_entries_as_read(feed_id)


def make_html(entries: Iterable[Entry]) -> str:
    """Bake a nice HTML-based E-mail featuring _entries_."""
    messagefile = pkgutil.get_data(__name__, "templates/message.html")
    entryfile = pkgutil.get_data(__name__, "templates/entry.html")
    cssfile = pkgutil.get_data(__name__, "style.css")
    assert messagefile
    assert entryfile
    assert cssfile

    template_message = Template(messagefile.decode())
    template_entry = Template(entryfile.decode())
    css = cssfile.decode()

    entries_html = "".join(template_entry.substitute(**asdict(e)) for e in entries)
    return template_message.substitute(entries=entries_html, style=css)


def make_mail(title: str, content: str, from_addr: str, to_addr: str) -> EmailMessage:
    """Carefully craft an Email Message."""
    msg = EmailMessage()
    msg.set_content(content)
    msg.set_type("text/html")
    msg.add_header("From", from_addr)
    msg.add_header("To", to_addr)
    msg.add_header("Subject", title)
    return msg


if __name__ == "__main__":
    main()
