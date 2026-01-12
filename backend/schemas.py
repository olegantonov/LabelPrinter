"""
Schemas Pydantic para validação de dados
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============== Cliente Schemas ==============

class EnderecoBase(BaseModel):
    """Schema base de endereço"""
    descricao: Optional[str] = None
    destinatario: Optional[str] = None
    logradouro: str
    numero: str
    complemento: Optional[str] = None
    bairro: str
    cidade: str
    estado: str = Field(..., max_length=2)
    cep: str = Field(..., pattern=r'^\d{5}-?\d{3}$')
    referencia: Optional[str] = None
    principal: bool = False


class EnderecoCreate(EnderecoBase):
    """Schema para criação de endereço"""
    pass


class EnderecoUpdate(BaseModel):
    """Schema para atualização de endereço"""
    descricao: Optional[str] = None
    destinatario: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    referencia: Optional[str] = None
    principal: Optional[bool] = None
    ativo: Optional[bool] = None


class EnderecoResponse(EnderecoBase):
    """Schema de resposta de endereço"""
    id: int
    cliente_id: int
    ativo: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ClienteBase(BaseModel):
    """Schema base de cliente"""
    nome: str
    documento: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    observacoes: Optional[str] = None


class ClienteCreate(ClienteBase):
    """Schema para criação de cliente"""
    enderecos: Optional[List[EnderecoCreate]] = []


class ClienteUpdate(BaseModel):
    """Schema para atualização de cliente"""
    nome: Optional[str] = None
    documento: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    observacoes: Optional[str] = None
    ativo: Optional[bool] = None


class ClienteResponse(ClienteBase):
    """Schema de resposta de cliente"""
    id: int
    ativo: bool
    created_at: datetime
    enderecos: List[EnderecoResponse] = []

    class Config:
        from_attributes = True


class ClienteListResponse(BaseModel):
    """Schema de resposta de lista de clientes"""
    id: int
    nome: str
    documento: Optional[str]
    telefone: Optional[str]
    email: Optional[str]
    ativo: bool
    qtd_enderecos: int = 0

    class Config:
        from_attributes = True


# ============== Impressora Schemas ==============

class ImpressoraBase(BaseModel):
    """Schema base de impressora"""
    nome: str
    nome_sistema: str
    tipo: str  # thermal, laser, inkjet
    modelo: Optional[str] = None
    localizacao: Optional[str] = None


class ImpressoraCreate(ImpressoraBase):
    """Schema para criação de impressora"""
    pass


class ImpressoraUpdate(BaseModel):
    """Schema para atualização de impressora"""
    nome: Optional[str] = None
    nome_sistema: Optional[str] = None
    tipo: Optional[str] = None
    modelo: Optional[str] = None
    localizacao: Optional[str] = None
    ativa: Optional[bool] = None


class ImpressoraResponse(ImpressoraBase):
    """Schema de resposta de impressora"""
    id: int
    ativa: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Configuração Etiqueta Schemas ==============

class ConfiguracaoEtiquetaBase(BaseModel):
    """Schema base de configuração de etiqueta"""
    tipo_etiqueta: str
    impressora_id: Optional[int] = None


class ConfiguracaoEtiquetaCreate(ConfiguracaoEtiquetaBase):
    """Schema para criação de configuração"""
    pass


class ConfiguracaoEtiquetaResponse(ConfiguracaoEtiquetaBase):
    """Schema de resposta de configuração"""
    id: int
    impressora: Optional[ImpressoraResponse] = None

    class Config:
        from_attributes = True


# ============== Impressão Schemas ==============

class ImpressaoRequest(BaseModel):
    """Schema para requisição de impressão"""
    cliente_id: int
    endereco_id: int
    tipo_etiqueta: str  # thermal_60x30, thermal_100x80, pimaco_a4, envelope_dl, envelope_c5
    quantidade: int = 1
    impressora_id: Optional[int] = None
    incluir_codigo_barras: bool = True
    incluir_remetente: bool = False


class ImpressaoPreviewRequest(BaseModel):
    """Schema para preview de impressão"""
    cliente_id: int
    endereco_id: int
    tipo_etiqueta: str
    incluir_codigo_barras: bool = True
    incluir_remetente: bool = False


class HistoricoImpressaoResponse(BaseModel):
    """Schema de resposta do histórico"""
    id: int
    cliente_id: int
    endereco_id: int
    tipo_etiqueta: str
    quantidade: int
    created_at: datetime
    cliente_nome: Optional[str] = None
    endereco_descricao: Optional[str] = None

    class Config:
        from_attributes = True


# ============== Remetente Schema ==============

class RemetenteConfig(BaseModel):
    """Schema de configuração do remetente"""
    nome: str
    logradouro: str
    numero: str
    complemento: Optional[str] = None
    bairro: str
    cidade: str
    estado: str
    cep: str
