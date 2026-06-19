import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta, timezone

from ..database import get_db
from ..models import User, Sessao, Item, Atribuicao

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@split.com")
ADMIN_PASS  = os.getenv("ADMIN_PASS", "admin123")
SECRET_KEY  = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
ALGORITHM   = "HS256"

bearer = HTTPBearer(auto_error=False)


def _admin_token():
    exp = datetime.now(timezone.utc) + timedelta(hours=8)
    return jwt.encode({"sub": "admin", "role": "admin", "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)


def get_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Acesso negado")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


@router.post("/login")
def admin_login(body: dict):
    if body.get("email") != ADMIN_EMAIL or body.get("senha") != ADMIN_PASS:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return {"token": _admin_token()}


@router.get("/users")
def listar_users(db: Session = Depends(get_db), _=Depends(get_admin)):
    users = db.query(User).order_by(User.criado_em.desc()).all()
    result = []
    for u in users:
        sessoes = db.query(Sessao).filter(Sessao.user_id == u.id).all()
        total_itens = sum(len(s.itens) for s in sessoes)
        result.append({
            "id": u.id,
            "email": u.email,
            "verificado": u.verificado,
            "criado_em": u.criado_em.strftime("%d/%m/%Y %H:%M") if u.criado_em else "",
            "n_sessoes": len(sessoes),
            "n_itens": total_itens,
        })
    return result


@router.get("/users/{user_id}/sessoes")
def sessoes_do_user(user_id: str, db: Session = Depends(get_db), _=Depends(get_admin)):
    sessoes = db.query(Sessao).filter(Sessao.user_id == user_id).order_by(Sessao.criado_em.desc()).all()
    result = []
    for s in sessoes:
        total = 0.0
        for it in s.itens:
            if it.modo_individual:
                total += sum(float(it.preco) * a.qtd for a in it.atribuicoes)
            elif it.atribuicoes:
                total += float(it.preco) * it.qtd
        gorjeta = total * float(s.gorjeta_pct) / 100
        result.append({
            "id": s.id,
            "nome": s.nome,
            "criado_em": s.criado_em.strftime("%d/%m/%Y %H:%M") if s.criado_em else "",
            "gorjeta_pct": float(s.gorjeta_pct),
            "n_pessoas": len(s.pessoas),
            "n_itens": len(s.itens),
            "total": total + gorjeta,
            "pessoas": [{"nome": p.nome, "emoji": p.emoji} for p in s.pessoas],
            "itens": [{"nome": it.nome, "emoji": it.emoji, "preco": float(it.preco), "qtd": it.qtd} for it in s.itens],
        })
    return result


@router.delete("/sessoes/{sessao_id}", status_code=204)
def deletar_sessao(sessao_id: str, db: Session = Depends(get_db), _=Depends(get_admin)):
    s = db.query(Sessao).filter(Sessao.id == sessao_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    db.delete(s)
    db.commit()
