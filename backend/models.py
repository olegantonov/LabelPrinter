"""
Modelos de dados para o sistema de impressão de etiquetas
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Cliente(Base):
    """Modelo de Cliente"""
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False, index=True)
    documento = Column(String(20), nullable=True)  # CPF ou CNPJ
    telefone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamento com endereços
    enderecos = relationship("Endereco", back_populates="cliente", cascade="all, delete-orphan")


class Endereco(Base):
    """Modelo de Endereço"""
    __tablename__ = "enderecos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    descricao = Column(String(100), nullable=True)  # Ex: "Residencial", "Comercial"
    destinatario = Column(String(255), nullable=True)  # Nome do destinatário se diferente
    logradouro = Column(String(255), nullable=False)
    numero = Column(String(20), nullable=False)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(100), nullable=False)
    cidade = Column(String(100), nullable=False)
    estado = Column(String(2), nullable=False)
    cep = Column(String(9), nullable=False)  # Formato: 00000-000
    referencia = Column(String(255), nullable=True)
    principal = Column(Boolean, default=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamento com cliente
    cliente = relationship("Cliente", back_populates="enderecos")


class Impressora(Base):
    """Modelo de Impressora"""
    __tablename__ = "impressoras"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    nome_sistema = Column(String(255), nullable=False)  # Nome no sistema de impressão
    tipo = Column(String(50), nullable=False)  # thermal, laser, inkjet
    modelo = Column(String(100), nullable=True)
    localizacao = Column(String(100), nullable=True)
    ativa = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConfiguracaoEtiqueta(Base):
    """Configuração de impressora padrão por tipo de etiqueta"""
    __tablename__ = "configuracoes_etiqueta"

    id = Column(Integer, primary_key=True, index=True)
    tipo_etiqueta = Column(String(50), nullable=False, unique=True)
    impressora_id = Column(Integer, ForeignKey("impressoras.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamento com impressora
    impressora = relationship("Impressora")


class HistoricoImpressao(Base):
    """Histórico de impressões realizadas"""
    __tablename__ = "historico_impressao"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    endereco_id = Column(Integer, ForeignKey("enderecos.id"), nullable=False)
    tipo_etiqueta = Column(String(50), nullable=False)
    impressora_id = Column(Integer, ForeignKey("impressoras.id"), nullable=True)
    quantidade = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    cliente = relationship("Cliente")
    endereco = relationship("Endereco")
    impressora = relationship("Impressora")
