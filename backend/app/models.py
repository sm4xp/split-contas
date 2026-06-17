import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import relationship
from .database import Base


def gen_id():
    return str(uuid.uuid4())[:12]


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, unique=True, nullable=False, index=True)
    senha_hash = Column(String, nullable=False)
    verificado = Column(Boolean, default=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    sessoes = relationship("Sessao", back_populates="user", cascade="all, delete-orphan")
    tokens = relationship("EmailToken", back_populates="user", cascade="all, delete-orphan")


class EmailToken(Base):
    __tablename__ = "email_tokens"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    expira_em = Column(DateTime(timezone=True), nullable=False)
    usado = Column(Boolean, default=False)
    user = relationship("User", back_populates="tokens")


class Sessao(Base):
    __tablename__ = "sessoes"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    nome = Column(String, default="Nova conta")
    gorjeta_pct = Column(Numeric(5, 2), default=12)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="sessoes")
    pessoas = relationship("Pessoa", back_populates="sessao", cascade="all, delete-orphan", order_by="Pessoa.ordem")
    itens = relationship("Item", back_populates="sessao", cascade="all, delete-orphan", order_by="Item.ordem")


class Pessoa(Base):
    __tablename__ = "pessoas"
    id = Column(String, primary_key=True, default=gen_id)
    sessao_id = Column(String, ForeignKey("sessoes.id"), nullable=False)
    nome = Column(String, nullable=False)
    emoji = Column(String, default="👤")
    cor_idx = Column(Integer, default=0)
    ordem = Column(Integer, default=0)
    sessao = relationship("Sessao", back_populates="pessoas")
    atribuicoes = relationship("Atribuicao", back_populates="pessoa", cascade="all, delete-orphan")


class Item(Base):
    __tablename__ = "itens"
    id = Column(String, primary_key=True, default=gen_id)
    sessao_id = Column(String, ForeignKey("sessoes.id"), nullable=False)
    nome = Column(String, nullable=False)
    emoji = Column(String, default="🍺")
    preco = Column(Numeric(10, 2), default=0)
    qtd = Column(Integer, default=1)
    modo_individual = Column(Boolean, default=False)
    ordem = Column(Integer, default=0)
    sessao = relationship("Sessao", back_populates="itens")
    atribuicoes = relationship("Atribuicao", back_populates="item", cascade="all, delete-orphan")


class Atribuicao(Base):
    __tablename__ = "atribuicoes"
    id = Column(String, primary_key=True, default=gen_id)
    item_id = Column(String, ForeignKey("itens.id"), nullable=False)
    pessoa_id = Column(String, ForeignKey("pessoas.id"), nullable=False)
    qtd = Column(Integer, default=1)
    item = relationship("Item", back_populates="atribuicoes")
    pessoa = relationship("Pessoa", back_populates="atribuicoes")
