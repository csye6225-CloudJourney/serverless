import os
import boto3
import psycopg2
import json
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables
DB_HOST = os.getenv("DB_HOST")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

# Function to connect to the database
def connect_to_database():
    return psycopg2.connect(
        host=DB_HOST,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )

# Function to send email
def send_verification_email(email, verification_link):
    try:
        message = Mail(
            from_email="noreply@yourdomain.com",
            to_emails=email,
            subject="Verify Your Email",
            html_content=f"""
            <p>Click the link below to verify your email:</p>
            <a href="{verification_link}">{verification_link}</a>
            <p>This link will expire in 2 minutes.</p>
            """
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        logger.info(f"Verification email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False

# Lambda Handler
def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    # Parse SNS event
    try:
        sns_message = event['Records'][0]['Sns']['Message']
        payload = json.loads(sns_message)
        email = payload["email"]
        user_id = payload["user_id"]
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse SNS message: {e}")
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid SNS message"})
        }

    # Generate verification link
    expiration_time = datetime.utcnow() + timedelta(minutes=2)
    verification_token = f"{user_id}:{expiration_time.isoformat()}"
    verification_link = f"https://yourdomain.com/verify?token={verification_token}"

    # Send the email
    email_sent = send_verification_email(email, verification_link)
    if not email_sent:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to send verification email"})
        }

    # Log the email to the database
    try:
        conn = connect_to_database()
        cursor = conn.cursor()
        query = """
            INSERT INTO email_verification (user_id, email, verification_token, expiration_time, is_verified)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, email, verification_token, expiration_time, False))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Email logged successfully for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Database error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to log email in database"})
        }

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Verification email sent successfully"})
    }