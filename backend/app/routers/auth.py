import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, EmailToken
from ..schemas import RegisterIn, LoginIn, TokenOut
from ..auth import hash_senha, verificar_senha, criar_jwt, get_current_user, enviar_email_verificacao

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    user = User(email=body.email.lower(), senha_hash=hash_senha(body.senha))
    db.add(user)
    db.flush()
    token_str = str(uuid.uuid4())
    token = EmailToken(
        user_id=user.id,
        token=token_str,
        expira_em=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(token)
    db.commit()
    enviar_email_verificacao(user.email, token_str)
    return {"message": "Cadastro realizado. Verifique seu e-mail para ativar a conta."}


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    tok = db.query(EmailToken).filter(EmailToken.token == token, EmailToken.usado == False).first()
    if not tok:
        return HTMLResponse("<h3>Link inválido ou já utilizado.</h3>", status_code=400)
    if tok.expira_em.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return HTMLResponse("<h3>Link expirado. Solicite um novo cadastro.</h3>", status_code=400)
    tok.usado = True
    tok.user.verificado = True
    db.commit()
    return HTMLResponse("""
    <html><head><meta charset="UTF-8">
    <meta http-equiv="refresh" content="3;url=/">
    </head><body style="font-family:sans-serif;text-align:center;padding:60px">
    <h2 style="color:#1D9E75">✅ E-mail verificado!</h2>
    <p>Redirecionando para o app...</p>
    </body></html>
    """)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verificar_senha(body.senha, user.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    if not user.verificado:
        raise HTTPException(status_code=403, detail="Verifique seu e-mail antes de entrar")
    return TokenOut(token=criar_jwt(user.id, user.email), email=user.email, user_id=user.id)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}


@router.post("/resend-verification")
def resend_verification(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verificar_senha(body.senha, user.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    if user.verificado:
        return {"message": "Conta já verificada"}
    token_str = str(uuid.uuid4())
    token = EmailToken(
        user_id=user.id,
        token=token_str,
        expira_em=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(token)
    db.commit()
    enviar_email_verificacao(user.email, token_str)
    return {"message": "E-mail de verificação reenviado"}
