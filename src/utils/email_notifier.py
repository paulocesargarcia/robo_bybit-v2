import os
import requests
from dotenv import load_dotenv
from src.utils.logger import logger

load_dotenv()

class EmailNotifier:
    def __init__(self):
        self.api_key = os.getenv('MAILGUN_API_KEY')
        self.domain = os.getenv('MAILGUN_DOMAIN')
        self.from_email = os.getenv('MAILGUN_FROM_EMAIL')
        self.to_email = os.getenv('MAILGUN_TO_EMAIL')
        self.use_notifier = os.getenv('USE_NOTIFIER', 'true').lower() == 'true'
        
        if not all([self.api_key, self.domain, self.from_email, self.to_email]):
            raise ValueError("Configurações do Mailgun não encontradas no .env")
            
        self.base_url = f"https://api.mailgun.net/v3/{self.domain}/messages"
        logger.info(f"EmailNotifier {'ativo' if self.use_notifier else 'desativado'}")

    def send_email(self, subject: str, content: dict, to_email: str = None) -> bool:
        if not self.use_notifier:
            return False
            
        try:
            html = f"""
                <div style="font-family: Arial; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #333;">{content.get('title', 'Notificação')}</h2>
                    <div style="background: #f5f5f5; padding: 15px; border-radius: 5px;">
                        <p><strong>Cripto:</strong> {content.get('symbol')}</p>
                        <p><strong>Lado:</strong> <span style="color: {'#28a745' if content.get('side') == 'long' else '#dc3545'}">{content.get('side', '').upper()}</span></p>
                        <p><strong>Preço:</strong> {content.get('price')}</p>
                        <p><strong>Quantidade:</strong> {content.get('quantity')}</p>
                        <p><strong>Alavancagem:</strong> {content.get('leverage', 'N/A')}x</p>
                        <p><strong>Stop Loss:</strong> {content.get('stop_loss', 'N/A')}</p>
                        <p><strong>Take Profit:</strong> {content.get('take_profit', 'N/A')}</p>
                    </div>
                </div>
            """

            response = requests.post(
                self.base_url,
                auth=("api", self.api_key),
                data={
                    "from": self.from_email,
                    "to": to_email or self.to_email,
                    "subject": subject,
                    "html": html
                }
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Erro ao enviar email: {str(e)}")
            return False 