"""
PATH: backend/app/api/routes/subscribe/email.py
PURPOSE: Welcome email for new newsletter subscribers via Resend
"""

import os
import logging
from typing import Optional

import resend

from app.api.routes.subscribe.tokens import get_unsubscribe_url

logger = logging.getLogger(__name__)


def send_thank_you_email(to_email: str, first_name: Optional[str] = None) -> bool:
    """
    Send a welcome email to new newsletter subscriber via Resend.
    Includes R&D Alpha research highlights and unsubscribe link.
    """
    # Set API key dynamically to ensure env is loaded
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        logger.warning("Resend API key not configured, skipping email")
        return False
    
    resend.api_key = api_key
    
    try:
        greeting = f"Hi {first_name}," if first_name else "Hello,"
        unsubscribe_url = get_unsubscribe_url(to_email)
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0f172a;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0f172a;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 560px; background-color: #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="padding: 48px 40px 32px 40px; text-align: center; border-bottom: 1px solid #334155;">
                            <div style="font-size: 28px; font-weight: 800; color: #f8fafc; letter-spacing: -0.5px; margin-bottom: 8px;">
                                R&D Alpha
                            </div>
                            <div style="font-size: 13px; color: #94a3b8; text-transform: uppercase; letter-spacing: 2px;">
                                FSE Research & Investments
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <h1 style="margin: 0 0 24px 0; font-size: 24px; font-weight: 700; color: #f8fafc;">
                                Welcome to R&D Alpha
                            </h1>
                            
                            <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.7; color: #cbd5e1;">
                                {greeting}
                            </p>
                            
                            <p style="margin: 0 0 28px 0; font-size: 16px; line-height: 1.7; color: #cbd5e1;">
                                Thank you for subscribing. You've joined a community of investors and researchers exploring <strong style="color: #f8fafc;">hidden alpha in R&D-intensive companies</strong>.
                            </p>
                            
                            <!-- Key Research Findings -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
                                <tr>
                                    <td style="background: linear-gradient(135deg, rgba(59,130,246,0.15) 0%, rgba(99,102,241,0.15) 100%); border-radius: 12px; padding: 24px; border-left: 4px solid #3b82f6;">
                                        <div style="font-size: 14px; font-weight: 600; color: #60a5fa; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px;">
                                            📊 Our Key Findings
                                        </div>
                                        <table role="presentation" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td style="padding: 8px 0; color: #e2e8f0; font-size: 15px; line-height: 1.6;">
                                                    <strong style="color: #60a5fa;">+7.55% annual premium</strong> — High R&amp;D portfolios outperform low R&amp;D portfolios in the frozen snapshot
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; color: #e2e8f0; font-size: 15px; line-height: 1.6;">
                                                    <strong style="color: #60a5fa;">Hidden value</strong> — R&D is expensed, not capitalized, creating systematic undervaluation
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; color: #e2e8f0; font-size: 15px; line-height: 1.6;">
                                                    <strong style="color: #60a5fa;">24-year backtest</strong> — Non-overlapping annual July–June testing (Jul2001–Jun2025) with point-in-time membership where spans are available
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- What to Expect Box -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 32px;">
                                <tr>
                                    <td style="background: linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(6,182,212,0.15) 100%); border-radius: 12px; padding: 24px; border-left: 4px solid #10b981;">
                                        <div style="font-size: 14px; font-weight: 600; color: #10b981; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px;">
                                            What You'll Receive
                                        </div>
                                        <table role="presentation" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #10b981; margin-right: 10px;">→</span> Monthly research updates & new findings
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #10b981; margin-right: 10px;">→</span> R&D factor performance & market insights
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #10b981; margin-right: 10px;">→</span> Early access to whitepapers & tools
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- CTA Button -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td align="center">
                                        <a href="https://research.finsoeasy.com" style="display: inline-block; background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%); color: #ffffff; font-size: 15px; font-weight: 600; text-decoration: none; padding: 14px 36px; border-radius: 8px;">
                                            Explore the Research
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 32px 40px; background-color: #0f172a; text-align: center; border-top: 1px solid #334155;">
                            <p style="margin: 0 0 8px 0; font-size: 14px; color: #94a3b8;">
                                Abhishek Sehgal
                            </p>
                            <p style="margin: 0 0 16px 0; font-size: 13px; color: #64748b;">
                                FSE Research and Investments
                            </p>
                            <div style="margin-bottom: 16px;">
                                <a href="https://research.finsoeasy.com" style="color: #10b981; font-size: 13px; text-decoration: none; margin: 0 8px;">Research</a>
                                <span style="color: #475569;">|</span>
                                <a href="https://research.finsoeasy.com/privacy" style="color: #64748b; font-size: 13px; text-decoration: none; margin: 0 8px;">Privacy</a>
                                <span style="color: #475569;">|</span>
                                <a href="https://research.finsoeasy.com/terms" style="color: #64748b; font-size: 13px; text-decoration: none; margin: 0 8px;">Terms</a>
                            </div>
                            <p style="margin: 0; font-size: 12px; color: #475569;">
                                © 2025 FSE Research and Investments. All rights reserved.
                            </p>
                        </td>
                    </tr>
                    
                </table>
                
                <!-- Unsubscribe -->
                <p style="margin: 20px 0 0 0; font-size: 12px; color: #64748b; text-align: center;">
                    Don't want these emails? <a href="{unsubscribe_url}" style="color: #94a3b8; text-decoration: underline;">Unsubscribe</a>
                </p>
            </td>
        </tr>
    </table>
</body>
</html>
        """.strip()
        
        params = {
            "from": "R&D Alpha <abhishek@finsoeasy.com>",
            "to": [to_email],
            "subject": "Welcome to R&D Alpha — Factor-Based Investment Research",
            "html": html_content,
        }
        
        response = resend.Emails.send(params)
        logger.info(f"Welcome email sent to {to_email}, id: {response.get('id', 'unknown')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
