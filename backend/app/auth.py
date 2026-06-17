import os
import uuid
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000")

bearer = HTTPBearer(auto_error=False)
_executor = ThreadPoolExecutor(max_workers=2)


def hash_senha(senha: str) -> str:
    return _bcrypt.hashpw(senha.encode(), _bcrypt.gensalt()).decode()


def verificar_senha(senha: str, hashed: str) -> bool:
    return _bcrypt.checkpw(senha.encode(), hashed.encode())


def criar_jwt(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": user_id, "email": email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_jwt(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    try:
        payload = decodificar_jwt(credentials.credentials)
        user_id: str = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    return user


def _enviar_email_sync(destinatario: str, assunto: str, html: str):
    if not SMTP_USER or not SMTP_PASS:
        print(f"[EMAIL SIMULADO] Para: {destinatario} | Assunto: {assunto}")
        print(html)
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = SMTP_USER
    msg["To"] = destinatario
    msg.attach(MIMEText(html, "html", "utf-8"))
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, destinatario, msg.as_string())


def enviar_email_verificacao(email: str, token: str):
    link = f"{FRONTEND_URL}/verify?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px">
      <h2 style="color:#1D9E75">&#127860; Divisor de Contas</h2>
      <p>Clique no botão abaixo para verificar seu e-mail e ativar sua conta:</p>
      <a href="{link}" style="display:inline-block;background:#1D9E75;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;margin:16px 0">
        Verificar e-mail
      </a>
      <p style="color:#888;font-size:12px">Link válido por 24 horas. Se não foi você, ignore este e-mail.</p>
    </div>
    """
    _executor.submit(_enviar_email_sync, email, "Verifique seu e-mail — Divisor de Contas", html)
