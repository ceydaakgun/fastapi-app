from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

import os
import json
import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization


def _load_secrets():
    load_dotenv()
    if os.getenv("AES_KEY"):
        if not os.path.exists("private.pem"):
            _write_private_key_from_env()
        return
    import boto3
    client = boto3.client("secretsmanager", region_name="eu-north-1")
    secret = client.get_secret_value(SecretId="fastapi-app/env")
    data = json.loads(secret["SecretString"])
    skip_keys = {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"}
    for k, v in data.items():
        if k not in skip_keys:
            os.environ.setdefault(k, v)
    if "PRIVATE_KEY" in data and not os.path.exists("private.pem"):
        with open("private.pem", "w") as f:
            f.write(data["PRIVATE_KEY"])


def _write_private_key_from_env():
    key = os.getenv("PRIVATE_KEY", "")
    if key:
        with open("private.pem", "w") as f:
            f.write(key)


_load_secrets()

from langchain_core.messages import HumanMessage
from chatbot import graph

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    encrypted_access: str


def check_access(decrypted_access: str):
    expected_secret = os.getenv("ACCESS_SECRET")

    if not expected_secret:
        raise HTTPException(status_code=500, detail="ACCESS_SECRET is not set")

    if decrypted_access != expected_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")


def run_chatbot(message: str):
    result = graph.invoke({"messages": [HumanMessage(content=message)]})
    return result["messages"][-1].content


@app.get("/")
def read_root():
    return {"message": os.getenv("APP_MESSAGE", "Chatbot API is running")}


@app.get("/public-key")
def get_public_key():
    try:
        with open("public.pem", "r") as key_file:
            return {"public_key": key_file.read()}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="public.pem not found")


@app.post("/chat/symmetric")
def chat_symmetric(body: ChatRequest):
    try:
        aes_key = os.getenv("AES_KEY")

        if not aes_key:
            raise HTTPException(status_code=500, detail="AES_KEY is not set")

        f = Fernet(aes_key.encode())

        decrypted_access = f.decrypt(
            base64.b64decode(body.encrypted_access)
        ).decode()

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Access decryption failed")

    check_access(decrypted_access)

    response = run_chatbot(body.message)

    return {"response": response}


@app.post("/chat/asymmetric")
def chat_asymmetric(body: ChatRequest):
    try:
        with open("private.pem", "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
            )

        decrypted_access = private_key.decrypt(
            base64.b64decode(body.encrypted_access),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        ).decode()

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="private.pem not found")
    except Exception:
        raise HTTPException(status_code=400, detail="Access decryption failed")

    check_access(decrypted_access)

    response = run_chatbot(body.message)

    return {"response": response}