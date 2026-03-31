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
        Formats a list of Alpaca-style orders into a premium dashboard-style HTML email.
        """
        if not self.sender_email or not self.app_password:
            logger.error("Email credentials missing. Skipping notification.")
            return

        subject = f"📊 Daily Trading Dashboard — {date.today().strftime('%b %d, %Y')}"
        
        # Calculate quick stats
        total_trades = len(orders)
        buys = sum(1 for o in orders if o['side'] == 'buy')
        sells = sum(1 for o in orders if o['side'] == 'sell')

        # Build trade rows
        rows = ""
        for o in orders:
            is_buy = o['side'] == 'buy'
            badge_bg = "#e6ffed" if is_buy else "#fff5f5"
            badge_text = "#22863a" if is_buy else "#cb2431"
            
            rows += f"""
            <tr style="border-bottom: 1px solid #edf2f7;">
                <td style="padding: 16px; font-weight: 600; color: #2d3748;">{o['symbol']}</td>
                <td style="padding: 16px;">
                    <span style="background-color: {badge_bg}; color: {badge_text}; padding: 4px 10px; border-radius: 99px; font-size: 12px; font-weight: bold; text-transform: uppercase;">
                        {o['side']}
                    </span>
                </td>
                <td style="padding: 16px; color: #4a5568;">{o['qty']}</td>
                <td style="padding: 16px; font-weight: 600; color: #2d3748;">${o['price']:.2f}</td>
                <td style="padding: 16px; color: #718096; font-size: 13px;">{o['time']}</td>
            </tr>
            """

        if not orders:
            rows = "<tr><td colspan='5' style='padding: 40px; text-align: center; color: #a0aec0; font-style: italic;'>No executions today. The bot remained patient.</td></tr>"

        html = f"""
        <html>
        <body style="margin: 0; padding: 0; background-color: #f7fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <div style="max-width: 650px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                
                <!-- HEADER SECTOR -->
                <div style="background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%); padding: 30px; text-align: center;">
                    <div style="color: #63b3ed; font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px;">Artificial Intelligence</div>
                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">TRADER DASHBOARD</h1>
                    <div style="color: #a0aec0; font-size: 14px; margin-top: 10px;">Session: {date.today().strftime('%A, %B %d')}</div>
                </div>

                <!-- SUMMARY STATS -->
                <div style="display: table; width: 100%; table-layout: fixed; border-bottom: 1px solid #edf2f7; background-color: #fcfcfd;">
                    <div style="display: table-cell; padding: 20px; text-align: center; border-right: 1px solid #edf2f7;">
                        <div style="color: #718096; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Total Trades</div>
                        <div style="font-size: 20px; font-weight: bold; color: #2d3748;">{total_trades}</div>
                    </div>
                    <div style="display: table-cell; padding: 20px; text-align: center; border-right: 1px solid #edf2f7;">
                        <div style="color: #718096; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Buys</div>
                        <div style="font-size: 20px; font-weight: bold; color: #38a169;">{buys}</div>
                    </div>
                    <div style="display: table-cell; padding: 20px; text-align: center;">
                        <div style="color: #718096; font-size: 12px; text-transform: uppercase; margin-bottom: 4px;">Sells</div>
                        <div style="font-size: 20px; font-weight: bold; color: #e53e3e;">{sells}</div>
                    </div>
                </div>

                <!-- TRADE LIST -->
                <div style="padding: 20px;">
                    <h3 style="color: #4a5568; font-size: 14px; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px;">Recent Activity</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="text-align: left; background-color: #f8fafc; border-bottom: 2px solid #edf2f7;">
                                <th style="padding: 12px 16px; font-size: 12px; color: #a0aec0; text-transform: uppercase;">Symbol</th>
                                <th style="padding: 12px 16px; font-size: 12px; color: #a0aec0; text-transform: uppercase;">Side</th>
                                <th style="padding: 12px 16px; font-size: 12px; color: #a0aec0; text-transform: uppercase;">Qty</th>
                                <th style="padding: 12px 16px; font-size: 12px; color: #a0aec0; text-transform: uppercase;">Avg Price</th>
                                <th style="padding: 12px 16px; font-size: 12px; color: #a0aec0; text-transform: uppercase;">Time (UTC)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows}
                        </tbody>
                    </table>
                </div>

                <!-- FOOTER -->
                <div style="background-color: #f7fafc; padding: 20px; text-align: center; border-top: 1px solid #edf2f7;">
                    <div style="display: inline-block; background-color: #ebf8ff; color: #3182ce; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: bold;">
                        🚀 YOLO MODE ACTIVE
                    </div>
                    <p style="color: #a0aec0; font-size: 12px; margin-top: 15px;">
                        This is an automated performance report from your AI Trading Bot.<br>
                        Server: GitHub Actions (Ubuntu) | Timezone: ART (Buenos Aires)
                    </p>
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
