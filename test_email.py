import asyncio
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST    = "smtp.gmail.com"
SMTP_PORT    = 587
SENDER_EMAIL = "damilareadebayo27@gmail.com"
SENDER_PASS  = "jfawjvdntewkoxzl"
TO_EMAIL     = "damilareadebayo27@gmail.com"

async def test():
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "NexusStore Test Email"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = TO_EMAIL
    msg.attach(MIMEText("<h1 style='color:green'>Email is working!</h1>", "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=SENDER_EMAIL,
            password=SENDER_PASS,
        )
        print("✅ SUCCESS - Email sent!")
    except Exception as e:
        print(f"❌ FAILED - Error: {e}")

asyncio.run(test())