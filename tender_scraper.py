import requests
from bs4 import BeautifulSoup
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Configuration (from GitHub Actions Secrets) ---
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
APP_PASSWORD = os.environ.get('APP_PASSWORD')
# Optionally set a different receiver:
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL', SENDER_EMAIL)

# --- File to store the last tender's URL ---
LAST_TENDER_FILE = 'last_tender.txt'


def get_last_tender_url():
    """Reads the last known tender URL from a file."""
    if os.path.exists(LAST_TENDER_FILE):
        with open(LAST_TENDER_FILE, 'r') as f:
            return f.read().strip()
    return None


def save_last_tender_url(url):
    """Saves the latest tender URL to a file."""
    print(f"Attempting to save URL to file: {LAST_TENDER_FILE}")
    try:
        with open(LAST_TENDER_FILE, 'w') as f:
            f.write(url)
        print(f"Successfully saved URL to file: {LAST_TENDER_FILE}")
    except IOError as e:
        print(f"Error: Could not write to file '{LAST_TENDER_FILE}'.")
        print(f"Reason: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while writing to the file.")
        print(f"Reason: {e}")


def get_latest_tender(url):
    """Scrapes the main tenders page for the latest tender details."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the list of tenders by first finding the heading and then its next sibling list.
        tender_list = soup.find('h2', string='Live Tenders').find_next_sibling('ul')

        if tender_list:
            # Find the very first <li> item, which is the newest tender.
            latest_tender_li = tender_list.find('li')
            if latest_tender_li:
                # Find the <a> tag within the list item
                link = latest_tender_li.find('a')
                if link:
                    return {
                        'title': link.get_text(strip=True),
                        'url': link.get('href')
                    }
    except requests.exceptions.RequestException as e:
        print(f"Error during main page scrape: {e}")
    except Exception as e:
        print(f"An error occurred during scraping: {e}")
    return None


def get_tender_content(url):
    """
    Since the GIZ page doesn't link to full articles, this function
    will simply return the title and link as the "background knowledge".
    """
    return f"Link to tender: {url}\n\nNo additional content pages were found for this tender. Please visit the main page for more information."


def send_alert_email(subject, body):
    """Sends an email alert using SMTP."""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print("Email alert sent successfully!")

    except smtplib.SMTPAuthenticationError:
        print("Authentication error: Please check your email credentials or app password.")
    except Exception as e:
        print(f"An error occurred while sending the email: {e}")


def main():
    """Main function to run the tender check and send an alert."""
    tenders_url = "https://www.giz.de/en/live-tenders-giz-india#live-tenders"

    last_tender_url = get_last_tender_url()
    latest_tender = get_latest_tender(tenders_url)

    if latest_tender and latest_tender['url'] != last_tender_url:
        print("New tender detected! Processing...")

        # Scrape the full content of the new tender
        full_content = get_tender_content(latest_tender['url'])

        # Prepare the email
        subject = f"New GIZ Tender Alert: {latest_tender['title']}"
        body = f"A new tender has been posted!\n\nTitle: {latest_tender['title']}\nURL: {latest_tender['url']}\n\n--- Tender Details ---\n\n{full_content}"

        # Send the email
        send_alert_email(subject, body)

        # Save the new tender's URL to prevent duplicate alerts
        save_last_tender_url(latest_tender['url'])

    else:
        print("No new tenders found.")


if __name__ == "__main__":
    main()
