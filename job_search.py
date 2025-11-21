#!/usr/bin/env python3
# job_search.py

import os
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# -------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------

KEYWORDS = ["java"]
LEVEL_WORDS = ["junior", "entry", "fresher", "graduate", "trainee", "0-1", "0-2"]

EXCLUDE = ["senior", "lead", "manager", "architect", "principal", "staff"]

SOURCES = [
    ("Wellfound", "https://wellfound.com/jobs?search=java+junior"),
    ("StartupJobs", "https://startup.jobs/?q=java+junior"),
    ("Dice", "https://www.dice.com/jobs?q=java+junior"),
    ("IndeedRSS", "https://www.indeed.com/rss?q=java+junior"),
    ("RemoteOK", "https://remoteok.com/remote-java-jobs"),
]

MAX_PER_SITE = 10

HEADERS = {"User-Agent": "Mozilla/5.0 JobBot/1.0"}

# -------------------------------------------------------
# HELPERS
# -------------------------------------------------------

def is_valid_role(title: str) -> bool:
    t = title.lower()
    if any(x in t for x in EXCLUDE):
        return False
    return any(k in t for k in KEYWORDS) and any(l in t for l in LEVEL_WORDS)


def fetch_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"[Error] Cannot fetch {url}: {e}")
        return None


def parse_generic(site, soup):
    jobs = []
    if soup is None:
        return jobs

    for a in soup.select("a")[:MAX_PER_SITE]:
        title = a.get_text(strip=True)
        link = a.get("href")
        if not title or not link:
            continue

        if not link.startswith("http"):
            link = f"https://{site.lower()}.com{link}"

        if is_valid_role(title):
            jobs.append({
                "title": title,
                "company": "",
                "link": link,
                "source": site
            })
    return jobs


def parse_remoteok():
    jobs = []
    try:
        r = requests.get("https://remoteok.com/remote-java-jobs", headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.select("tr.job")[:MAX_PER_SITE]:
            title_el = row.select_one("h2")
            title = title_el.get_text(strip=True) if title_el else ""
            link_el = row.select_one("a.preventLink")
            link = "https://remoteok.com" + link_el["href"] if link_el else ""

            if is_valid_role(title):
                jobs.append({
                    "title": title,
                    "company": row.get("data-company", ""),
                    "link": link,
                    "source": "RemoteOK"
                })
    except Exception as e:
        print("[RemoteOK Error]", e)
    return jobs


# -------------------------------------------------------
# COLLECT ALL JOBS
# -------------------------------------------------------

def collect_jobs():
    all_jobs = []

    for site, url in SOURCES:
        if site == "RemoteOK":
            all_jobs.extend(parse_remoteok())
            continue

        soup = fetch_html(url)
        all_jobs.extend(parse_generic(site, soup))

    # Deduplicate by link
    seen = set()
    unique = []
    for j in all_jobs:
        if j["link"] not in seen:
            seen.add(j["link"])
            unique.append(j)
    return unique


# -------------------------------------------------------
# BUILD HTML EMAIL
# -------------------------------------------------------

def build_html(jobs):
    now = datetime.now().strftime("%d %b %Y — %I:%M %p IST")

    if not jobs:
        return f"""
        <h2>🔥 Daily Java Job Update</h2>
        <p>No matching entry-level Java jobs found today.</p>
        <p><b>Time:</b> {now}</p>
        """

    html = f"""
    <h2>🔥 Daily Java Fresher Job Updates</h2>
    <p><b>Time:</b> {now}</p>
    <hr>
    """

    for i, j in enumerate(jobs, 1):
        html += f"""
        <p>
        <b>{i}) {j['title']}</b><br>
        🏢 <b>{j['source']}</b><br>
        🔗 <a href="{j['link']}">{j['link']}</a>
        </p>
        """

    return html


# -------------------------------------------------------
# SEND EMAIL (HTML)
# -------------------------------------------------------

def send_email(subject, html_body):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    to_email  = os.getenv("TO_EMAIL")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email

    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, 587) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, [to_email], msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print("[Email Error]", e)


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------

if __name__ == "__main__":
    jobs = collect_jobs()
    html = build_html(jobs)

    subject = f"[{len(jobs)}] Daily Java Fresher Jobs — {datetime.now().strftime('%Y-%m-%d')}"
    send_email(subject, html)

    print("Jobs found:", len(jobs))
    for j in jobs:
        print("-", j["title"], "|", j["source"])
