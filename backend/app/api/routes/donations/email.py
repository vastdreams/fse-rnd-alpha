"""
PATH: backend/app/api/routes/donations/email.py
PURPOSE: Thank-you email for donors via Resend
"""

import os
import logging
import resend

logger = logging.getLogger(__name__)


def send_donation_thank_you_email(to_email: str, amount: float, is_recurring: bool = False) -> bool:
    """Send a thank you email to donor via Resend. Includes R&D Alpha research highlights."""
    # Set API key dynamically to ensure env is loaded
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        logger.warning("Resend API key not configured, skipping donation email")
        return False
    
    resend.api_key = api_key
    donation_type = "monthly supporter" if is_recurring else "one-time"
    amount_str = f"${amount:.2f}"
    
    # Generate unsubscribe URL (import from subscribe module)
    from app.api.routes.subscribe import get_unsubscribe_url
    unsubscribe_url = get_unsubscribe_url(to_email)
    
    try:
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
                        <td style="padding: 48px 40px 32px 40px; text-align: center; background: linear-gradient(135deg, rgba(236,72,153,0.2) 0%, rgba(244,63,94,0.2) 100%); border-bottom: 1px solid #334155;">
                            <div style="font-size: 48px; margin-bottom: 16px;">💖</div>
                            <div style="font-size: 28px; font-weight: 800; color: #f8fafc; letter-spacing: -0.5px; margin-bottom: 4px;">
                                R&D Alpha
                            </div>
                            <div style="font-size: 13px; color: #94a3b8; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 16px;">
                                FSE Research & Investments
                            </div>
                            <div style="font-size: 16px; color: #f472b6;">
                                Your {amount_str} {donation_type} donation received
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <h1 style="margin: 0 0 24px 0; font-size: 24px; font-weight: 700; color: #f8fafc;">
                                Thank You for Your Support
                            </h1>
                            
                            <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 1.7; color: #cbd5e1;">
                                Your generosity directly supports our mission to provide <strong style="color: #f8fafc;">free, open investment research</strong> to everyone.
                            </p>
                            
                            <!-- Research Highlight -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 24px;">
                                <tr>
                                    <td style="background: linear-gradient(135deg, rgba(59,130,246,0.15) 0%, rgba(99,102,241,0.15) 100%); border-radius: 12px; padding: 20px; border-left: 4px solid #3b82f6;">
                                        <div style="font-size: 13px; font-weight: 600; color: #60a5fa; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">
                                            📊 Research Highlight
                                        </div>
                                        <p style="margin: 0; color: #e2e8f0; font-size: 15px; line-height: 1.6;">
                                            Our R&D Alpha research documents a <strong style="color: #60a5fa;">+7.55% annual high-minus-low premium</strong> (71% win rate across 24 annual periods) and an implementable long-only variant retains ~99% of the premium after estimated trading costs.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- What Your Donation Supports -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 32px;">
                                <tr>
                                    <td style="background: linear-gradient(135deg, rgba(236,72,153,0.1) 0%, rgba(244,63,94,0.1) 100%); border-radius: 12px; padding: 24px; border-left: 4px solid #ec4899;">
                                        <div style="font-size: 14px; font-weight: 600; color: #f472b6; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px;">
                                            Your Support Enables
                                        </div>
                                        <table role="presentation" cellspacing="0" cellpadding="0">
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #f472b6; margin-right: 10px;">→</span> Premium SEC & financial data feeds
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #f472b6; margin-right: 10px;">→</span> 24/7 research infrastructure
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #f472b6; margin-right: 10px;">→</span> New factor research & strategies
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 6px 0; color: #e2e8f0; font-size: 15px;">
                                                    <span style="color: #f472b6; margin-right: 10px;">→</span> Open-source tools for all investors
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
                                        <a href="https://research.finsoeasy.com" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%); color: #ffffff; font-size: 15px; font-weight: 600; text-decoration: none; padding: 14px 36px; border-radius: 8px;">
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
                                With gratitude,
                            </p>
                            <p style="margin: 0 0 8px 0; font-size: 15px; font-weight: 600; color: #f8fafc;">
                                Abhishek Sehgal
                            </p>
                            <p style="margin: 0 0 16px 0; font-size: 13px; color: #64748b;">
                                FSE Research and Investments
                            </p>
                            <div style="margin-bottom: 16px;">
                                <a href="https://research.finsoeasy.com" style="color: #f472b6; font-size: 13px; text-decoration: none; margin: 0 8px;">Research</a>
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
            "from": "FSE Research <abhishek@finsoeasy.com>",
            "to": [to_email],
            "subject": f"Thank You for Your Support – {amount_str} Donation Received",
            "html": html_content,
        }
        
        response = resend.Emails.send(params)
        logger.info(f"Donation email sent to {to_email}, id: {response.get('id', 'unknown')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send donation email to {to_email}: {e}")
        return False
