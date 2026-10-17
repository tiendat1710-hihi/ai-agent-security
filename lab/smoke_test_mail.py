import smtplib
from email.message import EmailMessage

import requests

import config


def send(server, to, subject, body):
    msg = EmailMessage()
    msg["From"] = "test@company.test"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(server["smtp_host"], server["smtp_port"], timeout=10) as s:
        s.send_message(msg)


def count(server):
    r = requests.get(server["api"] + "/api/v2/messages", timeout=10)
    r.raise_for_status()
    return r.json()["total"]


if __name__ == "__main__":
    send(config.INTERNAL_MAIL, "me@company.test", "Test noi bo", "Thu thu hop thu NOI BO")
    send(config.EXTERNAL_MAIL, "hacker@evil.test", "Test ben ngoai", "Thu thu hop thu BEN NGOAI")
    print("So thu trong hop thu NOI BO   :", count(config.INTERNAL_MAIL))
    print("So thu trong hop thu BEN NGOAI:", count(config.EXTERNAL_MAIL))