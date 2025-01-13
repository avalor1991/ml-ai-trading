import requests
import logging

class Notifier:
    def __init__(self, telegram_token, telegram_chat_id):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.logger = logging.getLogger(__name__)

    def send_telegram_message(self, message):
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "HTML"}
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                self.logger.info(f"Trading signal sent to Telegram: {message}")
            else:
                self.logger.error(f"Failed to send message to Telegram. Status Code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.logger.error(f"Error while sending Telegram message: {e}")