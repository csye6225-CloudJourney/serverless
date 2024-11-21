import os
import json
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Header
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
ENV_PREFIX = os.getenv("ENV_PREFIX", "").strip()

# Adjust domain prefix
if ENV_PREFIX:
    domain_prefix = f"{ENV_PREFIX}."
else:
    domain_prefix = ""

def send_verification_email(email, verification_link):
    try:
        # Email content
        subject = "Verify Your Email Address"
        plain_text_content = f"""
Dear User,

Thank you for signing up. Please verify your email address by clicking the link below:
{verification_link}

This link will expire in 2 minutes. If you did not sign up, please ignore this email.

To manage your email preferences or unsubscribe, please visit:
https://{domain_prefix}cloudjourney.me/unsubscribe

Regards,
The CloudJourney Team
"""
        html_content = f"""
<html>
    <body>
        <p>Dear User,</p>
        <p>Thank you for signing up. Please verify your email address by clicking the link below:</p>
        <p><a href="{verification_link}">{verification_link}</a></p>
        <p>This link will expire in 2 minutes. If you did not sign up, please ignore this email.</p>
        <p>To manage your email preferences or unsubscribe, please click <a href="https://{domain_prefix}cloudjourney.me/unsubscribe">here</a>.</p>
        <p>Regards,<br>The CloudJourney Team</p>
    </body>
</html>
"""

        # Create SendGrid email
        message = Mail(
            from_email='noreply@em7116.cloudjourney.me',  # Ensure this email is verified in SendGrid
            to_emails=email,
            subject=subject,
            plain_text_content=plain_text_content,
            html_content=html_content
        )

        # Add List-Unsubscribe header
        list_unsubscribe_email = "mailto:unsubscribe@em7116.cloudjourney.me"
        list_unsubscribe_url = f"https://{domain_prefix}cloudjourney.me/unsubscribe"
        unsubscribe_header = Header(
            "List-Unsubscribe",
            f"<{list_unsubscribe_email}>, <{list_unsubscribe_url}>"
        )
        message.personalizations[0].add_header(unsubscribe_header)

        # Send email using SendGrid
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Email sent to {email}, status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")

        if response.status_code != 202:
            logger.error(f"SendGrid API Error: {response.status_code} - {response.body}")
            return False

        return True
    except Exception as e:
        logger.error(f"Exception when sending email: {e}")
        return False
    
def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Check if event is from SNS
        if 'Records' in event:
            sns_message = event['Records'][0]['Sns']['Message']
            payload = json.loads(sns_message)
        else:
            # Direct invocation
            payload = event
        
        # Extract email and verification token
        email = payload.get("email")
        verification_token = payload.get("verification_token")

        if not email or not verification_token:
            raise ValueError("Missing required fields: email or verification_token")
    except Exception as e:
        logger.error(f"Error parsing message: {e}")
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid event format"})
        }

    # Construct verification link
    try:
        verification_link = f"http://{domain_prefix}cloudjourney.me/verify?token={verification_token}"
        logger.info(f"Constructed verification link for email: {email}")
    except Exception as e:
        logger.error(f"Error constructing verification link: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to construct verification link"})
        }

    # Send the email
    if not send_verification_email(email, verification_link):
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to send verification email"})
        }

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Verification email sent successfully"})
    }