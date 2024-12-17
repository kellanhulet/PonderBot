import requests
from sqlalchemy import create_engine, Column, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import pandas as pd
import schedule
import time
import logging
import yaml
import os
import telegram
from telegram.error import TelegramError

# Setup logging
logging.basicConfig(
    filename='dexscreener_bot.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

# Load configuration
def load_config(config_path='config.yaml'):
    if not os.path.exists(config_path):
        logging.error(f"Configuration file {config_path} not found.")
        raise FileNotFoundError(f"Configuration file {config_path} not found.")
    with open(config_path, 'r') as file:
        try:
            config = yaml.safe_load(file)
            logging.info("Configuration loaded successfully.")
            return config
        except yaml.YAMLError as e:
            logging.error(f"Error parsing config file: {e}")
            raise

config = load_config()

# Database setup
Base = declarative_base()

class CoinEvent(Base):
    __tablename__ = 'coin_events'
    id = Column(String, primary_key=True)
    name = Column(String)
    price = Column(Float)
    event_type = Column(String)
    dev_address = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

engine = create_engine('sqlite:///coins.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Constants
DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex/tokens"

# Initialize Telegram Bot
telegram_bot = telegram.Bot(token=config['telegram']['bot_token'])

# Functions

def fetch_coin_data():
    try:
        response = requests.get(DEXSCREENER_API_URL)
        response.raise_for_status()
        data = response.json()
        logging.info("Fetched coin data successfully.")
        return data
    except requests.RequestException as e:
        logging.error(f"Error fetching data: {e}")
        return None

def is_token_good_rugcheck(token_id, config):
    """
    Verifies if a token is marked as 'Good' on rugcheck.xyz.
    """
    try:
        api_key = config['rugcheck']['api_key']
        base_url = config['rugcheck']['base_url']
        good_status = config['rugcheck']['good_status']

        # Construct the API request URL
        # Assuming the API expects a GET request with the token ID as a path parameter
        url = f"{base_url}/{token_id}"
        headers = {'Authorization': f"Bearer {api_key}"}

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        result = response.json()

        # Assuming the API returns a 'status' field
        status = result.get('status', 'Unknown')
        if status == good_status:
            return True
        else:
            logging.info(f"Token {token_id} is marked as '{status}' on rugcheck.xyz. Skipping.")
            return False
    except requests.RequestException as e:
        logging.error(f"Error connecting to rugcheck.xyz API for token {token_id}: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error during rugcheck.xyz verification for token {token_id}: {e}")
        return False

def is_supply_bundled(token_data, config):
    """
    Checks if a token's supply is bundled.
    """
    try:
        # Assuming the API provides a field indicating if supply is bundled
        # The field name is configurable
        bundled_field = config['supply_check']['bundled_supply_field']
        is_bundled = token_data.get(bundled_field, False)
        return is_bundled
    except Exception as e:
        logging.error(f"Error checking supply bundling for token {token_data.get('id', 'Unknown')}: {e}")
        return False

def update_blacklists_if_bundled(token_data, config):
    """
    Updates the coin and developer blacklists if the token's supply is bundled.
    """
    try:
        coin_id = token_data.get('id')
        dev_address = token_data.get('developer_address', '')
        coin_name = token_data.get('name')

        if coin_id and dev_address:
            # Update coin blacklist
            config['coin_blacklist'].append(coin_id)
            config['coin_blacklist'].append(coin_name)

            # Update developer blacklist
            config['dev_blacklist'].append(dev_address)

            logging.info(f"Token {coin_name} ({coin_id}) has bundled supply. Added to blacklists.")
    except Exception as e:
        logging.error(f"Error updating blacklists for token {token_data.get('id', 'Unknown')}: {e}")

def is_volume_valid_algorithm(coin, config):
    """
    Validates the volume of a coin using algorithm-based checks.
    """
    try:
        # Extract volume data
        daily_volume = float(coin.get('daily_volume', 0))  # Assuming 'daily_volume' is provided
        volume_change = float(coin.get('volume_change_percentage_24h', 0))  # Assuming this field exists

        # Apply minimum volume threshold
        min_volume = config['fake_volume_detection']['algorithm']['min_volume_threshold']
        if daily_volume < min_volume:
            logging.info(f"Coin {coin.get('name')} ({coin.get('id')}) has volume {daily_volume} below threshold {min_volume}. Skipping.")
            return False

        # Apply maximum volume change percentage
        max_volume_change = config['fake_volume_detection']['algorithm']['max_volume_change_percentage']
        if abs(volume_change) > max_volume_change:
            logging.info(f"Coin {coin.get('name')} ({coin.get('id')}) has volume change {volume_change}% beyond threshold {max_volume_change}%. Skipping.")
            return False

        return True
    except Exception as e:
        logging.error(f"Error in algorithm-based volume validation for {coin.get('name', 'Unknown')}: {e}")
        return False

def is_volume_valid_pocket_universe(coin, config):
    """
    Validates the volume of a coin using the Pocket Universe API.
    """
    try:
        api_key = config['fake_volume_detection']['pocket_universe']['api_key']
        base_url = config['fake_volume_detection']['pocket_universe']['base_url']

        # Construct the API request
        # Assuming the API expects a GET request with the coin ID as a parameter
        params = {'coin_id': coin.get('id')}
        headers = {'Authorization': f"Bearer {api_key}"}

        response = requests.get(base_url, params=params, headers=headers)
        response.raise_for_status()
        result = response.json()

        # Assume the API returns a field 'is_volume_fake' as True/False
        is_fake = result.get('is_volume_fake', False)
        if is_fake:
            logging.info(f"Coin {coin.get('name')} ({coin.get('id')}) has fake volume according to Pocket Universe API. Skipping.")
            return False
        return True
    except requests.RequestException as e:
        logging.error(f"Error connecting to Pocket Universe API for {coin.get('name', 'Unknown')}: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error during Pocket Universe API validation for {coin.get('name', 'Unknown')}: {e}")
        return False

def is_volume_valid(coin, config):
    """
    Determines if a coin's volume is valid based on the selected method.
    """
    method = config['fake_volume_detection']['method'].lower()
    if method == 'algorithm':
        return is_volume_valid_algorithm(coin, config)
    elif method == 'pocket_universe':
        return is_volume_valid_pocket_universe(coin, config)
    else:
        logging.warning(f"Unknown fake_volume_detection method '{method}'. Defaulting to algorithm-based validation.")
        return is_volume_valid_algorithm(coin, config)

def is_token_selected_for_trade(coin, config):
    """
    Determines if a token is selected for trading.
    This function can be customized based on specific criteria.
    For demonstration, let's assume all valid coins are selected.
    """
    # Implement your selection logic here
    # For example, select coins with certain event types or other criteria
    # Here, we'll select all coins that passed previous filters
    return True

def send_telegram_message(message, config):
    """
    Sends a message to the configured Telegram chat.
    """
    try:
        chat_id = config['telegram']['chat_id']
        telegram_bot.send_message(chat_id=chat_id, text=message)
        logging.info(f"Sent Telegram message: {message}")
    except TelegramError as e:
        logging.error(f"Error sending Telegram message: {e}")

def trade_via_bonkbot(coin, config, action="buy", amount=1):
    """
    Sends trade commands to BonkBot via Telegram.
    """
    try:
        bonkbot_chat_id = config['bonkbot']['telegram_chat_id']
        if action.lower() == "buy":
            command = config['bonkbot']['trade_commands']['buy_command'].format(token_id=coin['id'], amount=amount)
        elif action.lower() == "sell":
            command = config['bonkbot']['trade_commands']['sell_command'].format(token_id=coin['id'], amount=amount)
        else:
            logging.error(f"Invalid trade action: {action}")
            return

        # Send the command to BonkBot's Telegram chat
        telegram_bot.send_message(chat_id=bonkbot_chat_id, text=command)
        logging.info(f"Sent trade command to BonkBot: {command}")

        # Notify via Telegram about the trade
        notification = f"Executed {action.upper()} for {coin['name']} ({coin['id']}) with amount {amount}."
        send_telegram_message(notification, config)

    except TelegramError as e:
        logging.error(f"Error sending trade command to BonkBot: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during trade via BonkBot: {e}")

def parse_coin_data(raw_data, config):
    coins = []
    coin_blacklist = set(config.get('coin_blacklist', []))
    dev_blacklist = set(config.get('dev_blacklist', []))
    filters = config.get('filters', {})
    min_change = filters.get('min_price_change_percentage_24h', 0)
    max_change = filters.get('max_price_change_percentage_24h', 0)
    monitored_events = set(filters.get('monitored_events', []))

    for item in raw_data.get('tokens', []):
        try:
            coin_id = item.get('id')
            coin_name = item.get('name')
            price = float(item.get('price', 0))
            price_change = float(item.get('price_change_percentage_24h', 0))
            dev_address = item.get('developer_address', '')  # Adjust based on actual data field

            # Apply Coin Blacklist
            if coin_id in coin_blacklist or coin_name in coin_blacklist:
                logging.info(f"Coin {coin_name} ({coin_id}) is blacklisted. Skipping.")
                continue

            # Apply Dev Blacklist
            if dev_address in dev_blacklist:
                logging.info(f"Developer {dev_address} is blacklisted. Skipping coin {coin_name}.")
                continue

            # Determine Event Type
            event_type = determine_event_type(price_change, item, config)

            # Apply Monitored Events Filter
            if event_type not in monitored_events:
                continue

            # Verify token status on rugcheck.xyz
            if not is_token_good_rugcheck(coin_id, config):
                continue

            # Check for bundled supply
            if is_supply_bundled(item, config):
                update_blacklists_if_bundled(item, config)
                logging.info(f"Token {coin_name} ({coin_id}) has bundled supply. Added to blacklists. Skipping.")
                continue

            # Validate Volume
            if not is_volume_valid(item, config):
                continue

            # At this point, the coin is valid and can be considered for trading
            coin = {
                'id': coin_id,
                'name': coin_name,
                'price': price,
                'event_type': event_type,
                'dev_address': dev_address,
                'timestamp': datetime.datetime.utcnow()
            }

            # Add to the list of processed coins
            coins.append(coin)

            # Optionally, select the coin for trading
            if is_token_selected_for_trade(coin, config):
                # Execute trade (buy) via BonkBot
                trade_via_bonkbot(coin, config, action="buy", amount=1)  # Adjust amount as needed

                # Send Telegram notification about the trade
                trade_message = f"Executed BUY for {coin['name']} ({coin['id']}) at price {price} USD."
                send_telegram_message(trade_message, config)

        except Exception as e:
            logging.error(f"Error parsing coin data for {item.get('name', 'Unknown')}: {e}")
    logging.info(f"Parsed {len(coins)} coins after applying filters, blacklists, rugcheck.xyz verification, supply check, and volume validation.")
    return coins

def determine_event_type(price_change, item, config):
    filters = config.get('filters', {})
    min_change = filters.get('min_price_change_percentage_24h', 0)
    max_change = filters.get('max_price_change_percentage_24h', 0)

    # Example logic based on price change
    if price_change >= min_change:
        return 'pumped'
    elif price_change <= max_change:
        return 'rugged'
    elif item.get('is_tier_1', False):
        return 'tier-1'
    elif item.get('is_listed_on_cex', False):
        return 'listed_on_cex'
    else:
        return 'other'

def save_to_database(coins):
    session = Session()
    try:
        for coin in coins:
            # Assuming 'id' and 'timestamp' uniquely identify an event
            existing = session.query(CoinEvent).filter_by(id=coin['id'], timestamp=coin['timestamp']).first()
            if not existing:
                new_event = CoinEvent(**coin)
                session.add(new_event)
        session.commit()
        logging.info("Saved coins to database.")
    except Exception as e:
        session.rollback()
        logging.error(f"Error saving to database: {e}")
    finally:
        session.close()

def analyze_data():
    session = Session()
    try:
        data = session.query(CoinEvent).all()
        if not data:
            logging.info("No data to analyze.")
            return
        df = pd.DataFrame([{
            'id': event.id,
            'name': event.name,
            'price': event.price,
            'event_type': event.event_type,
            'dev_address': event.dev_address,
            'timestamp': event.timestamp
        } for event in data])

        # Example Analysis: Count events by type
        event_counts = df['event_type'].value_counts()
        logging.info(f"Event Counts:\n{event_counts}")

        # Example: Price distribution
        price_stats = df['price'].describe()
        logging.info(f"Price Statistics:\n{price_stats}")

        # More complex pattern recognition can be implemented here
    except Exception as e:
        logging.error(f"Error during analysis: {e}")
    finally:
        session.close()

def job():
    logging.info("Job started.")
    raw_data = fetch_coin_data()
    if raw_data:
        coins = parse_coin_data(raw_data, config)
        save_to_database(coins)
        analyze_data()
    logging.info("Job finished.")

# Schedule the job every hour
schedule.every(1).hours.do(job)

# Run the scheduler
if __name__ == "__main__":
    logging.info("Dexscreener Bot started.")
    send_telegram_message("Dexscreener Bot has started.", config)
    while True:
        schedule.run_pending()
        time.sleep(1)
