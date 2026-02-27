import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

def send_sms_notification(phone_number, message):
    """
    Wrapper function to send an SMS notification.
    Currently prints to the console. Can be integrated with MSG91, Twilio, etc. later.
    """
    if not phone_number:
        return False
        
    try:
        # TODO: Integrate with actual SMS Gateway API here
        print(f"\n{'='*50}")
        print(f"📱 SMS MOCK DISPATCH")
        print(f"To: {phone_number}")
        print(f"Message: {message}")
        print(f"{'='*50}\n")
        logger.info(f"Mock SMS sent to {phone_number}: {message}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
        return False

def send_email_notification(department_email, subject, message):
    """
    Wrapper to send an email notification to a department using Django's SMTP backend.
    """
    if not department_email:
        return False
        
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[department_email],
            fail_silently=False,
        )
        logger.info(f"Email sent successfully to {department_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {department_email}: {str(e)}")
        # For local testing without SMTP configured, print it too so we can see it works
        print(f"\n{'='*50}")
        print(f"📧 EMAIL DISPATCH FAILED (Likely SMTP not configured)")
        print(f"To: {department_email}")
        print(f"Subject: {subject}")
        print(f"Message:\n{message}")
        print(f"Error: {str(e)}")
        print(f"{'='*50}\n")
        return False
