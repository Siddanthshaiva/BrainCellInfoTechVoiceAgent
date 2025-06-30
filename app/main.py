from fastapi import FastAPI, Request, HTTPException
import json
import httpx
from datetime import timezone, datetime
import smtplib
from email.message import EmailMessage
from pydantic import BaseModel, EmailStr
from app.config import FAILED_CALL_SUMMARY,CALL_STATUS_ENDED,END_OF_CALL_REPORT, EMAIL_SUBJECT,CALL_STATUS_COMPLETED,FIREBASE_ACTION,EMAIL_ADDRESS, EMAIL_PASSWORD, ATTACHMENT_PATH,CALL_STATUS_FAILED, FIREBASE_ENDPOINT
import os
app = FastAPI()
# EMAIL_ADDRESS = 'notifier.tester12@gmail.com'
# EMAIL_PASSWORD = 'kery xsiu eouv kefo'
# ATTACHMENT_PATH = '/home/siddanth/VoiceGenie/brochure.pdf'
# FIREBASE_ENDPOINT = "https://updatecallanalysis-4v4wa6c35a-el.a.run.app"


def send_brochure_email(recipient: str):
    if not recipient:
        raise ValueError("Recipient email is empty.")

    try:
        response = httpx.get(ATTACHMENT_PATH)
        response.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Failed to download brochure: {e}")
    file_data = response.content
    file_name = ATTACHMENT_PATH.split("/")[-1]

    msg = EmailMessage()
    msg['Subject'] = EMAIL_SUBJECT
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = recipient
    msg.set_content("Hi there,\n\nPlease find attached the brochure you requested.\n\nBest regards,\nNotifier Team")

    # with open(ATTACHMENT_PATH, 'rb') as f:
    #     file_data = f.read()
    #     file_name = os.path.basename(ATTACHMENT_PATH)
    msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=file_name)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

class EmailRequest(BaseModel):
    email: EmailStr

@app.post("/send-brochure")
async def send_brochure(request: EmailRequest):
    try:
        send_brochure_email(request.email)
        return {"message": f"Brochure sent to {request.email}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Webhook endpoint for VAPI call events
@app.post("/vapi-webhook")
async def vapi_webhook(req: Request):
    payload = await req.json()
    print("payload",payload)
    if payload['message']['type'] == END_OF_CALL_REPORT:
        if payload['message']['call']['status'] == CALL_STATUS_ENDED and payload['message']['endedReason']== 'customer-did-not-answer' and not payload['message']['analysis'] and not payload['message']['artifact']:
            print("call ended")
            firebase_data = {
            "action": FIREBASE_ACTION,
            "data": {
                "leadId" : payload['message']['call']['id'],
                "callStatus": CALL_STATUS_FAILED,   
                "startedAt": payload['message']['call']['startedAt'],
                "endedAt": payload['message']['call']['endedAt'],
                "customerPhone": payload['message']['call']['customer']['number'], 
                "callRecordingUrl": None,
                "duration": None,        
                "callAnalysis": {
                    "summary": FAILED_CALL_SUMMARY,
                    "successEvaluation": None
                }
            }
        }
            async with httpx.AsyncClient() as client:
                response = await client.post(FIREBASE_ENDPOINT, json=firebase_data)
                print("Firebase CREATE post call status:", response.status_code)
                print("Firebase CREATE post call response:", response.json())
        if payload['message']['call']['status'] != CALL_STATUS_ENDED and payload['message']['analysis'] and payload['message']['artifact']:
            print("call not ended")
            firebase_data = {
            "action": "create",
            "data": {
                "leadId" : payload['message']['call']['id'],
                "callStatus": CALL_STATUS_COMPLETED,   
                "startedAt": payload['message']['startedAt'],
                "endedAt": payload['message']['endedAt'],
                "customerPhone": payload['message']['call']['customer']['number'],   
                "callRecordingUrl": payload['message']['artifact']['recordingUrl'],
                "duration": payload['message']['durationSeconds'],        
                "callAnalysis": {
                    "summary": payload['message']['analysis']['summary'],
                    "successEvaluation": payload['message']['analysis']['successEvaluation']
                }
            }
        }
            async with httpx.AsyncClient() as client:
                response = await client.post(FIREBASE_ENDPOINT, json=firebase_data)
                print("Firebase CREATE post call status:", response.status_code)
                print("Firebase CREATE post call response:", response.json())
    else:
        print("status - not end of call report")