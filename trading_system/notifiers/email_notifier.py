import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date
from typing import List
from config import config

logger = logging.getLogger(__name__)

class EmailNotifier:
    def __init__(self):
        # We'll pull these from config (which reads from .env or GH Secrets)
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = getattr(config, "EMAIL_USER", None)
        self.app_password = getattr(config, "EMAIL_PASSWORD", None)
        self.recipient_email = getattr(config, "EMAIL_RECIPIENT", None)

    def send_daily_report(self, orders: List[dict]):
        """
        Formats a list of Alpaca-style orders into a clean HTML email.
        """
        if not self.sender_email or not self.app_password:
            logger.error("Email credentials missing. Skipping notification.")
            return

        subject = f"📊 AI Trader — Daily Report [{date.today().strftime('%Y-%m-%d')}]"
        
        # Build HTML table for orders
        rows = ""
        for o in orders:
            row_color = "#e6ffed" if o['side'] == 'buy' else "#fff5f5"
            rows += f"""
            <tr style="background-color: {row_color}; border-bottom: 1px solid #ddd;">
                <td style="padding: 10px; font-weight: bold;">{o['symbol']}</td>
                <td style="padding: 10px; color: {'green' if o['side'] == 'buy' else 'red'}; text-transform: uppercase;">{o['side']}</td>
                <td style="padding: 10px;">{o['qty']}</td>
                <td style="padding: 10px;">${o['price']:.2f}</td>
                <td style="padding: 10px; font-size: 0.85em; color: #666;">{o['time']}</td>
            </tr>
            """

        if not orders:
            rows = "<tr><td colspan='5' style='padding: 20px; text-align: center; color: #666;'>No trades executed today. Market was quiet.</td></tr>"

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #eee; padding: 20px; border-radius: 10px;">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">🤖 Autonomous Trading Report</h2>
                <p>Hello, here are the operations executed by your AI bot today:</p>
                
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                    <thead style="background-color: #f8f9fa;">
                        <tr>
                            <th style="padding: 10px; text-align: left;">Symbol</th>
                            <th style="padding: 10px; text-align: left;">Action</th>
                            <th style="padding: 10px; text-align: left;">Qty</th>
                            <th style="padding: 10px; text-align: left;">Avg Price</th>
                            <th style="padding: 10px; text-align: left;">Time (UTC)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
                
                <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; font-size: 0.8em; color: #999;">
                    <p>Bot Status: 🚀 YOLO MODE ACTIVE<br>
                    Frequency: 45 Min Heartbeat<br>
                    Timezone: ART (Buenos Aires)</p>
                </div>
            </div>
        </body>
        </html>
        """

        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email or self.sender_email
            msg['Subject'] = subject
            msg.attach(MIMEText(html, 'html'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.app_password)
                server.send_message(msg)
            
            logger.info("✅ Daily report email sent successfully!")
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
