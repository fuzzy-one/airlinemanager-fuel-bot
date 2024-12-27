import os
import re
import time
from dotenv import load_dotenv
import requests
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler("fuel_bot.log")  # Log to file
    ]
)

logger = logging.getLogger()

# Load credentials from .env file
load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# URLs
LOGIN_URL = "https://www.airlinemanager.com/weblogin/login.php"
FUEL_URL = "https://www.airlinemanager.com/fuel.php"
CO2_URL = "https://www.airlinemanager.com/co2.php"
SEND_MSG_URL = "https://www.airlinemanager.com/alliance_chat.php?mode=do"

# Threshold values
FUEL_PRICE_THRESHOLD = 500  # Example threshold for fuel price
CO2_PRICE_THRESHOLD = 120  # Example threshold for CO2 price

# Session setup
session = requests.Session()

# Headers for login
login_headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

# Login payload
login_payload = {
    "lEmail": EMAIL,
    "lPass": PASSWORD,
    "fbSig": "null",
}

# Perform login
login_response = session.post(LOGIN_URL, headers=login_headers, data=login_payload)

if login_response.status_code == 200 and "PHPSESSID" in session.cookies:
    logger.info("Login successful!")
else:
    logger.error("Login failed!")
    logger.error("Response status code: %s", login_response.status_code)
    logger.error("Response content: %s", login_response.text)
    exit()


def fetch_page(url, description):
    """Fetch a page and handle errors."""
    try:
        response = session.get(url, headers={"User-Agent": login_headers["User-Agent"]})
        if response.status_code == 200:
            logger.info("Successfully fetched %s page!", description)
            return response.text
        else:
            logger.error("Failed to fetch %s page!", description)
            logger.error("Status Code: %s", response.status_code)
            logger.error("Redirect URL: %s", response.url)
            return None
    except Exception as e:
        logger.exception("Error fetching %s page: %s", description, e)
        return None


def fetch_fuel_timer_and_prices():
    """Fetch the fuel market timer and prices."""
    content = fetch_page(FUEL_URL, "fuel market")
    if content is None:
        return None

    timer_match = re.search(r"fuelTimer'\)\.countdown\(\{\s*until:\s*(\d+),", content)
    prices_match = re.search(r"fuel_startFuelChart\(\[(.*?)\],", content)

    if timer_match and prices_match:
        timer = int(timer_match.group(1))
        prices = prices_match.group(1).split(",")
        return timer, prices
    else:
        logger.warning("Could not find fuel market data.")
        return None


def fetch_co2_prices():
    """Fetch the CO2 market prices."""
    content = fetch_page(CO2_URL, "CO2 market")
    if content is None:
        return None

    prices_match = re.search(r"co2_startCo2Chart\(\[(.*?)\],", content)

    if prices_match:
        prices = prices_match.group(1).split(",")
        return prices
    else:
        logger.warning("Could not find CO2 market data.")
        return None


def send_message(message):
    """Send a message via a POST request using the existing session."""
    utc_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    message_with_time = f"{message} - @ {utc_time}"

    message_payload = {
        'alMsg': message_with_time,
        'fbSig': 'false'
    }

    send_msg_headers = {
        'User-Agent': login_headers["User-Agent"],
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9,ro;q=0.8',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://www.airlinemanager.com',
        'Referer': 'https://www.airlinemanager.com/?gameType=web',
        'X-Requested-With': 'XMLHttpRequest',
    }

    response = session.post(SEND_MSG_URL, data=message_payload, headers=send_msg_headers)

    if response.status_code == 200:
        logger.info("Message sent successfully!")
    else:
        logger.error("Failed to send message.")
        logger.error("Status Code: %s", response.status_code)
        logger.error("Response content: %s", response.text)


while True:
    # Fetch Fuel Data
    fuel_data = fetch_fuel_timer_and_prices()
    if fuel_data:
        fuel_timer, fuel_prices = fuel_data
        logger.info("Fuel Timer (seconds): %s", fuel_timer)
        logger.info("Fuel Prices: %s", fuel_prices)
        logger.info("Last Fuel Price: %s", fuel_prices[-1])
        
        if float(fuel_prices[-1]) < FUEL_PRICE_THRESHOLD:
            send_message(f"[ fuel-bot ] Fuel price is below {FUEL_PRICE_THRESHOLD}. Last price: {fuel_prices[-1]}.")

    # Fetch CO2 Data
    co2_prices = fetch_co2_prices()
    if co2_prices:
        logger.info("CO2 Prices: %s", co2_prices)
        logger.info("Last CO2 Price: %s", co2_prices[-1])

        if float(co2_prices[-1]) < CO2_PRICE_THRESHOLD:
            send_message(f"[ fuel-bot ] CO2 price is below {CO2_PRICE_THRESHOLD}. Last price: {co2_prices[-1]}.")

    # Sleep until the next refresh
    sleep_time = fuel_timer + 5 if fuel_data else 60
    logger.info("Sleeping for %s seconds until the next refresh...", sleep_time)
    time.sleep(sleep_time)
