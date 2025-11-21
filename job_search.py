#!/usr/bin/env python3
# job_search.py

import os
import smtplib
import requests
from bs4 import BeautifulSoup
from email.message import EmailMessage
from datetime import datetime

# Job sources
SOURCES = [
    ("Wellfound", "https://wellfound.com/jobs?search=java+junior"),
    ("StartupJobs", "https://startup.jobs/?q=java+junior"),
    ("Dice", "https://www.dice.com/jobs?q=java+junior"),
    ("IndeedRSS", "https://www.indeed.com/rss?q=java+junior"),
]

MAX_PER_SITE = 10

def fetch_html(url):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "job-bot"})
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_generic(site, soup):
    jobs = []
    for a in soup.select("a")[:MAX_PER_SITE]:
        title = a.get_text(strip=True)
        link = a.get("href")
        if not link or not title:
            continue
        link = link if link.startswith("http") else f"https://{site.lower()}.com{link}"

        t = title.lower()
        if "java" in t and any(x in t for x in ["junior", "entry", "fresher", "graduate"]):
            jobs.append({
                "title": title,
                "company": "",
                "link": link,
                "source": site
            })
    return jobs

def collect_jobs():
    all_jobs = []
    for site, url in SOURCES:
        soup = fetch_html(url)
        if not soup:
            continue
        jobs = parse_generic(site, soup)
        all_jobs.extend(jobs)

    # dedupe
    seen = set()
    unique = []
    for j in all_jobs:
        if j["link"] not in seen:
            seen.add(j["link"])
            unique.append(j)
    return unique

def build_email(jobs):
    now = datetime.now().strftime("%Y-%m-%d %H:%M IST")
    if not jobs:
        body = f"No new entry-level Java startup jobs found as of {now}."
        return "Daily Jobs — No results", body

    lines = []
    for i, j in enumerate(jobs, 1):
        lines.append(f"{i}) {j['title']} — {j['source']}\n   {j['link']}")

    body = f"Found {len(jobs)} new entry-level Java jobs at startups — {now}\n\n" + "\n\n".join(lines)
    subject = f"[{len(jobs)}] Java Startup Roles — {datetime.now().strftime('%Y-%m-%d')}"
    return subject, body

def send_email(subject, body):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    to_email  = os.getenv("TO_EMAIL")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, 587) as s:
        s.starttls()
        s.login(smtp_user, smtp_pass)
        s.send_message(msg)

    print("Email sent!")

if __name__ == "__main__":
    jobs = collect_jobs()
    subject, body = build_email(jobs)
    send_email(subject, body)
