import os, re, base64
import anthropic as anthropic_sdk
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Sessao, Pessoa, Item, Atribuicao
from ..schemas import (
    SessaoIn, SessaoUpdate, SessaoOut, SessaoListItem,
    PessoaIn, PessoaOut,
    ItemIn, ItemUpdate, ItemOut,
    AtribuicaoIn, AtribuicaoOut,
)
from ..auth import get_current_user

router = APIRouter(prefix="/sessoes", tags=["sessoes"])


def _sessao_or_404(sessao_id: str, user: User, db: Session) -> Sessao:
    s = db.query(Sessao).filter(Sessao.id == sessao_id, Sessao.user_id == user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    return s


def _sessao_to_out(s: Sessao) -> dict:
    return {
        "id": s.id,
        "nome": s.nome,
        "gorjeta_pct": s.gorjeta_pct,
        "criado_em": s.criado_em.isoformat() if s.criado_em else "",
        "pessoas": [
            {"id": p.id, "nome": p.nome, "emoji": p.emoji, "cor_idx": p.cor_idx, "ordem": p.ordem}
            for p in s.pessoas
        ],
        "itens": [
            {
                "id": it.id, "nome": it.nome, "emoji": it.emoji,
                "preco": float(it.preco), "qtd": it.qtd,
                "modo_individual": it.modo_individual, "nota": it.nota, "ordem": it.ordem,
                "atribuicoes": [
                    {"id": a.id, "pessoa_id": a.pessoa_id, "qtd": a.qtd}
                    for a in it.atribuicoes
                ],
            }
            for it in s.itens
        ],
    }


# ── Sessões ────────────────────────────────────────────────────────────────────

@router.get("")
def listar_sessoes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessoes = db.query(Sessao).filter(Sessao.user_id == user.id).order_by(Sessao.criado_em.desc()).all()
    return [
        {
            "id": s.id, "nome": s.nome, "gorjeta_pct": float(s.gorjeta_pct),
            "criado_em": s.criado_em.isoformat() if s.criado_em else "",
            "n_pessoas": len(s.pessoas), "n_itens": len(s.itens),
        }
        for s in sessoes
    ]


@router.post("", status_code=201)
def criar_sessao(body: SessaoIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = Sessao(user_id=user.id, nome=body.nome)
    db.add(s)
    db.commit()
    db.refresh(s)
    return _sessao_to_out(s)


@router.get("/{sessao_id}")
def get_sessao(sessao_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _sessao_to_out(_sessao_or_404(sessao_id, user, db))


@router.put("/{sessao_id}")
def atualizar_sessao(sessao_id: str, body: SessaoUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _sessao_or_404(sessao_id, user, db)
    if body.nome is not None:
        s.nome = body.nome
    if body.gorjeta_pct is not None:
        s.gorjeta_pct = body.gorjeta_pct
    db.commit()
    return _sessao_to_out(s)


@router.delete("/{sessao_id}", status_code=204)
def deletar_sessao(sessao_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _sessao_or_404(sessao_id, user, db)
    db.delete(s)
    db.commit()


# ── Pessoas ────────────────────────────────────────────────────────────────────

@router.post("/{sessao_id}/pessoas", status_code=201)
def adicionar_pessoa(sessao_id: str, body: PessoaIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _sessao_or_404(sessao_id, user, db)
    ordem = len(s.pessoas)
    p = Pessoa(sessao_id=s.id, nome=body.nome, emoji=body.emoji, cor_idx=body.cor_idx, ordem=ordem)
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "nome": p.nome, "emoji": p.emoji, "cor_idx": p.cor_idx, "ordem": p.ordem}


@router.delete("/{sessao_id}/pessoas/{pessoa_id}", status_code=204)
def remover_pessoa(sessao_id: str, pessoa_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _sessao_or_404(sessao_id, user, db)
    p = db.query(Pessoa).filter(Pessoa.id == pessoa_id, Pessoa.sessao_id == s.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")
    db.delete(p)
    db.commit()


# ── Itens ──────────────────────────────────────────────────────────────────────

@router.post("/{sessao_id}/itens", status_code=201)
def adicionar_item(sessao_id: str, body: ItemIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _sessao_or_404(sessao_id, user, db)
    ordem = len(s.itens)
    it = Item(sessao_id=s.id, nome=body.nome, emoji=body.emoji, preco=body.preco, qtd=body.qtd, ordem=ordem)
    db.add(it)
    db.commit()
    db.refresh(it)
    return {"id": it.id, "nome": it.nome, "emoji": it.emoji, "preco": float(it.preco),
            "qtd": it.qtd, "modo_individual": it.modo_individual, "nota": it.nota, "ordem": it.ordem, "atribuicoes": []}


@router.put("/{sessao_id}/itens/{item_id}")
def atualizar_item(sessao_id: str, item_id: str, body: ItemUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _sessao_or_404(sessao_id, user, db)
    it = db.query(Item).filter(Item.id == item_id, Item.sessao_id == s.id).first()
    if not it:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(it, field, val)
    db.commit()
    db.refresh(it)
    return {"id": it.id, "nome": it.nome, "emoji": it.emoji, "preco": float(it.preco),
            "qtd": it.qtd, "modo_individual": it.modo_individual, "nota": it.nota, "ordem": it.ordem,
            "atribuicoes": [{"id": a.id, "pessoa_id": a.pessoa_id, "qtd": a.qtd} for a in it.atribuicoes]}


@router.delete("/{sessao_id}/itens/{item_id}", status_code=204)
def remover_item(sessao_id: str, item_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = _sessao_or_404(sessao_id, user, db)
    it = db.query(Item).filter(Item.id == item_id, Item.sessao_id == s.id).first()
    if not it:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    db.delete(it)
    db.commit()


# ── Atribuições ────────────────────────────────────────────────────────────────

@router.put("/{sessao_id}/itens/{item_id}/atribuicoes")
def atribuir(
    sessao_id: str, item_id: str,
    body: list[AtribuicaoIn],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = _sessao_or_404(sessao_id, user, db)
    it = db.query(Item).filter(Item.id == item_id, Item.sessao_id == s.id).first()
    if not it:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    db.query(Atribuicao).filter(Atribuicao.item_id == it.id).delete()
    for a in body:
        db.add(Atribuicao(item_id=it.id, pessoa_id=a.pessoa_id, qtd=a.qtd))
    db.commit()
    db.refresh(it)
    return [{"id": a.id, "pessoa_id": a.pessoa_id, "qtd": a.qtd} for a in it.atribuicoes]


# ── Scanner de recibo ──────────────────────────────────────────────────────────

@router.post("/{sessao_id}/scan-receipt")
async def scan_receipt(
    sessao_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _sessao_or_404(sessao_id, user, db)
    image_bytes = await file.read()
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    media_type = file.content_type or "image/jpeg"

    client = anthropic_sdk.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": b64},
                    },
                    {
                        "type": "text",
                        "text": 'Analise este recibo/nota fiscal e retorne APENAS um JSON array com os itens. Formato: [{"nome": string, "preco": number (valor unitário em reais), "qtd": integer, "emoji": string (emoji relevante)}]. Sem texto extra, apenas o JSON.',
                    },
                ],
            }
        ],
    )
    text = message.content[0].text
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if not match:
        raise HTTPException(status_code=422, detail="Não foi possível extrair itens do recibo")
    import json
    try:
        itens_data = json.loads(match.group())
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Resposta do modelo inválida")
    return itens_data
