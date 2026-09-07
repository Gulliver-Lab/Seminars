import base64
import datetime
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-untyped]
from googleapiclient.discovery import build  # type: ignore[import-untyped]

from seminars.models import Email

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DEFAULT_CREDENTIALS_PATH = Path("credentials.json")
DEFAULT_TOKEN_PATH = Path("token.json")


def fetch_emails(
    credentials_path: str | Path = DEFAULT_CREDENTIALS_PATH,
    token_path: str | Path = DEFAULT_TOKEN_PATH,
    query: str = "",
    max_results: int = 100,
) -> list[Email]:
    credentials = _load_credentials(Path(credentials_path), Path(token_path))
    service = build("gmail", "v1", credentials=credentials)

    messages = _list_message_ids(service, query=query, max_results=max_results)
    return [
        parse_gmail_message(
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="raw")
            .execute()
        )
        for message_id in messages
    ]


def _load_credentials(
    credentials_path: Path,
    token_path: Path,
) -> Credentials:
    credentials = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(token_path, SCOPES)

    if credentials and credentials.valid:
        return credentials

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    else:
        if not credentials_path.exists():
            raise FileNotFoundError(
                f"Missing Gmail OAuth client secrets file: {credentials_path}"
            )
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        credentials = flow.run_local_server(port=0)

    token_path.write_text(credentials.to_json(), encoding="utf-8")
    return credentials


def _list_message_ids(service: Any, query: str, max_results: int) -> list[str]:
    message_ids: list[str] = []
    page_token = None

    while len(message_ids) < max_results:
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=min(500, max_results - len(message_ids)),
                pageToken=page_token,
            )
            .execute()
        )
        message_ids.extend(message["id"] for message in response.get("messages", []))
        page_token = response.get("nextPageToken")
        if page_token is None:
            break

    return message_ids


def parse_gmail_message(message: dict[str, Any]) -> Email:
    raw_message = message.get("raw")
    if not isinstance(raw_message, str):
        raise ValueError("Gmail message is missing raw content")

    parsed = BytesParser(policy=policy.default).parsebytes(
        base64.urlsafe_b64decode(raw_message)
    )
    if not isinstance(parsed, EmailMessage):
        raise ValueError("Gmail message did not parse as an email message")

    return Email(
        gmail_id=message["id"],
        date=_message_date(parsed, message),
        sender=parsed.get("from", ""),
        recipient=parsed.get("to", ""),
        content=_message_content(parsed),
    )


def _message_date(parsed: EmailMessage, message: dict[str, Any]) -> datetime.datetime:
    date_header = parsed.get("date")
    if date_header is not None:
        return parsedate_to_datetime(date_header)

    internal_date = message.get("internalDate")
    if internal_date is not None:
        return datetime.datetime.fromtimestamp(
            int(internal_date) / 1000,
            tz=datetime.UTC,
        )

    raise ValueError("Gmail message is missing both Date and internalDate")


def _message_content(message: EmailMessage) -> str:
    body = message.get_body(preferencelist=("plain", "html"))
    if body is None:
        return ""

    content = body.get_content()
    if body.get_content_type() == "text/html":
        return _html_to_text(content)
    return content.strip()


def _html_to_text(value: str) -> str:
    parser = _HTMLTextParser()
    parser.feed(value)
    parser.close()
    return parser.text.strip()


class _HTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    @property
    def text(self) -> str:
        return " ".join(" ".join(self._chunks).split())

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)
