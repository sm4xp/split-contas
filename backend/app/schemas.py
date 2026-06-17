from pydantic import BaseModel, EmailStr
from typing import List, Optional
from decimal import Decimal


class RegisterIn(BaseModel):
    email: EmailStr
    senha: str


class LoginIn(BaseModel):
    email: EmailStr
    senha: str


class TokenOut(BaseModel):
    token: str
    email: str
    user_id: str


class AtribuicaoIn(BaseModel):
    pessoa_id: str
    qtd: int = 1


class AtribuicaoOut(BaseModel):
    id: str
    pessoa_id: str
    qtd: int

    class Config:
        from_attributes = True


class PessoaIn(BaseModel):
    nome: str
    emoji: str = "👤"
    cor_idx: int = 0


class PessoaOut(BaseModel):
    id: str
    nome: str
    emoji: str
    cor_idx: int
    ordem: int

    class Config:
        from_attributes = True


class ItemIn(BaseModel):
    nome: str
    emoji: str = "🍺"
    preco: Decimal = Decimal("0")
    qtd: int = 1
    nota: Optional[str] = None


class ItemUpdate(BaseModel):
    nome: Optional[str] = None
    emoji: Optional[str] = None
    preco: Optional[Decimal] = None
    qtd: Optional[int] = None
    modo_individual: Optional[bool] = None
    nota: Optional[str] = None


class ItemOut(BaseModel):
    id: str
    nome: str
    emoji: str
    preco: Decimal
    qtd: int
    modo_individual: bool
    nota: Optional[str] = None
    ordem: int
    atribuicoes: List[AtribuicaoOut] = []

    class Config:
        from_attributes = True


class SessaoIn(BaseModel):
    nome: str = "Nova conta"


class SessaoUpdate(BaseModel):
    nome: Optional[str] = None
    gorjeta_pct: Optional[Decimal] = None


class SessaoOut(BaseModel):
    id: str
    nome: str
    gorjeta_pct: Decimal
    criado_em: str
    pessoas: List[PessoaOut] = []
    itens: List[ItemOut] = []

    class Config:
        from_attributes = True


class SessaoListItem(BaseModel):
    id: str
    nome: str
    gorjeta_pct: Decimal
    criado_em: str
    n_pessoas: int
    n_itens: int

    class Config:
        from_attributes = True
