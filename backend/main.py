"""
API Principal do Sistema de Impressao de Etiquetas
Integracoes: BrasilAPI (CEP), Benu ERP
Padrao: Correios (CEPNet, Data Matrix)
"""
from fastapi import FastAPI, Depends, HTTPException, Query, Response, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import io
import json
import os

from database import get_db, init_db
from models import Cliente, Endereco, Impressora, ConfiguracaoEtiqueta, HistoricoImpressao
from schemas import (
    ClienteCreate, ClienteUpdate, ClienteResponse, ClienteListResponse,
    EnderecoCreate, EnderecoUpdate, EnderecoResponse,
    ImpressoraCreate, ImpressoraUpdate, ImpressoraResponse,
    ConfiguracaoEtiquetaCreate, ConfiguracaoEtiquetaResponse,
    ImpressaoRequest, ImpressaoPreviewRequest, HistoricoImpressaoResponse,
    RemetenteConfig
)
from config import settings, LABEL_SIZES
from label_generator import label_generator
from printer_service import printer_service
from services.cep_service import cep_service
from services.benu_service import benu_service
from services.settings_service import system_settings

# Inicializar aplicacao
app = FastAPI(
    title="Sistema de Impressao de Etiquetas",
    description="API para gerenciamento e impressao de etiquetas de endereco com integracao BrasilAPI e Benu ERP",
    version="2.0.0"
)

# Configurar arquivos estaticos e templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend/static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend/templates"))


# ============== Schemas Adicionais ==============

class CepConsultaRequest(BaseModel):
    cep: str

class SystemSettingsUpdate(BaseModel):
    section: str
    data: Dict[str, Any]

class BenuTokenUpdate(BaseModel):
    token: str


# ============== Eventos de Startup ==============

@app.on_event("startup")
async def startup_event():
    """Inicializa o banco de dados e configuracoes"""
    init_db()

    # Criar configuracoes padrao para tipos de etiqueta
    db = next(get_db())
    for tipo in LABEL_SIZES.keys():
        existing = db.query(ConfiguracaoEtiqueta).filter(
            ConfiguracaoEtiqueta.tipo_etiqueta == tipo
        ).first()
        if not existing:
            config = ConfiguracaoEtiqueta(tipo_etiqueta=tipo)
            db.add(config)
    db.commit()
    db.close()

    # Carregar configuracoes do remetente
    remetente = system_settings.get_remetente()
    if remetente and remetente.get('nome'):
        label_generator.set_remetente(remetente)

    # Carregar configuracoes de etiqueta
    etiqueta_config = system_settings.get_etiqueta_config()
    label_generator.set_config(etiqueta_config)

    # Configurar token do Benu se existir
    benu_token = system_settings.get_benu_token()
    if benu_token:
        benu_service.set_token(benu_token)


# ============== Frontend Routes ==============

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Pagina inicial"""
    return templates.TemplateResponse("index.html", {"request": request})


# ============== API: Consulta de CEP (BrasilAPI) ==============

@app.get("/api/cep/{cep}")
async def consultar_cep(cep: str):
    """
    Consulta CEP via BrasilAPI
    Retorna endereco completo com cache de 30 dias
    """
    # Validar CEP
    if not cep_service.validate_cep(cep):
        raise HTTPException(status_code=400, detail="CEP invalido. Deve conter 8 digitos.")

    # Consultar
    resultado = await cep_service.fetch_cep_v1(cep)

    if resultado is None:
        raise HTTPException(status_code=404, detail="CEP nao encontrado")

    # Mapear para formato do sistema
    return {
        "success": True,
        "data": cep_service.map_to_address(resultado),
        "raw": resultado
    }


@app.get("/api/cep/{cep}/v2")
async def consultar_cep_v2(cep: str):
    """
    Consulta CEP via BrasilAPI v2 (com geolocalizacao)
    """
    if not cep_service.validate_cep(cep):
        raise HTTPException(status_code=400, detail="CEP invalido")

    resultado = await cep_service.fetch_cep_v2(cep)

    if resultado is None:
        raise HTTPException(status_code=404, detail="CEP nao encontrado")

    return {"success": True, "data": resultado}


@app.get("/api/cep/cache/stats")
def cep_cache_stats():
    """Retorna estatisticas do cache de CEP"""
    return cep_service.get_cache_stats()


@app.delete("/api/cep/cache")
def limpar_cache_cep():
    """Limpa o cache de CEP"""
    cep_service.clear_cache()
    return {"message": "Cache limpo com sucesso"}


# ============== API: Configuracoes do Sistema ==============

@app.get("/api/settings")
def obter_configuracoes():
    """Retorna todas as configuracoes do sistema (tokens mascarados)"""
    return system_settings.get_all()


@app.get("/api/settings/{section}")
def obter_configuracao_secao(section: str):
    """Retorna configuracoes de uma secao especifica"""
    config = system_settings.get(section)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Secao '{section}' nao encontrada")
    return config


@app.put("/api/settings/{section}")
def atualizar_configuracao(section: str, data: Dict[str, Any] = Body(...)):
    """Atualiza configuracoes de uma secao"""
    success = system_settings.update(section, data)
    if not success:
        raise HTTPException(status_code=400, detail="Erro ao atualizar configuracoes")

    # Atualizar servicos se necessario
    if section == "remetente":
        label_generator.set_remetente(data)
    elif section == "etiquetas":
        label_generator.set_config(data)
    elif section == "benu_api" and "token" in data:
        benu_service.set_token(data["token"])

    return {"message": "Configuracoes atualizadas", "section": section}


@app.post("/api/settings/benu/token")
def atualizar_token_benu(request: BenuTokenUpdate):
    """Atualiza o token do Benu ERP"""
    system_settings.set_benu_token(request.token)
    benu_service.set_token(request.token)
    return {"message": "Token do Benu ERP atualizado"}


@app.get("/api/settings/benu/test")
async def testar_conexao_benu():
    """Testa a conexao com o Benu ERP"""
    result = await benu_service.test_connection()
    return result


@app.post("/api/settings/reset/{section}")
def resetar_configuracao(section: str):
    """Reseta uma secao para valores padrao"""
    success = system_settings.reset_section(section)
    if not success:
        raise HTTPException(status_code=400, detail="Secao nao encontrada")
    return {"message": f"Secao '{section}' resetada para valores padrao"}


@app.get("/api/settings/validate")
def validar_configuracoes():
    """Valida todas as configuracoes"""
    return {
        "benu": system_settings.validate_benu_config(),
        "remetente": system_settings.validate_remetente()
    }


# ============== API: Benu ERP ==============

@app.get("/api/benu/cards/{cd_funil}")
async def benu_consultar_cards(cd_funil: int, offset: int = 0, max_results: int = 50):
    """Consulta cards do CRM no Benu ERP"""
    result = await benu_service.consultar_cards(cd_funil, offset, max_results)
    if result.get("error"):
        raise HTTPException(
            status_code=result.get("code", 500),
            detail=result.get("message")
        )
    return result


# ============== API: Clientes ==============

@app.get("/api/clientes", response_model=List[ClienteListResponse])
def listar_clientes(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    ativo: Optional[bool] = True,
    db: Session = Depends(get_db)
):
    """Lista todos os clientes"""
    query = db.query(Cliente)

    if ativo is not None:
        query = query.filter(Cliente.ativo == ativo)

    if search:
        query = query.filter(
            Cliente.nome.ilike(f"%{search}%") |
            Cliente.documento.ilike(f"%{search}%") |
            Cliente.email.ilike(f"%{search}%")
        )

    clientes = query.order_by(Cliente.nome).offset(skip).limit(limit).all()

    result = []
    for cliente in clientes:
        cliente_dict = {
            "id": cliente.id,
            "nome": cliente.nome,
            "documento": cliente.documento,
            "telefone": cliente.telefone,
            "email": cliente.email,
            "ativo": cliente.ativo,
            "qtd_enderecos": len([e for e in cliente.enderecos if e.ativo])
        }
        result.append(cliente_dict)

    return result


@app.get("/api/clientes/{cliente_id}", response_model=ClienteResponse)
def obter_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Obtem um cliente especifico com seus enderecos"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    return cliente


@app.post("/api/clientes", response_model=ClienteResponse)
def criar_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    """Cria um novo cliente"""
    db_cliente = Cliente(
        nome=cliente.nome,
        documento=cliente.documento,
        telefone=cliente.telefone,
        email=cliente.email,
        observacoes=cliente.observacoes
    )
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)

    for endereco_data in cliente.enderecos:
        db_endereco = Endereco(
            cliente_id=db_cliente.id,
            **endereco_data.model_dump()
        )
        db.add(db_endereco)

    db.commit()
    db.refresh(db_cliente)
    return db_cliente


@app.put("/api/clientes/{cliente_id}", response_model=ClienteResponse)
def atualizar_cliente(cliente_id: int, cliente: ClienteUpdate, db: Session = Depends(get_db)):
    """Atualiza um cliente existente"""
    db_cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    update_data = cliente.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_cliente, key, value)

    db.commit()
    db.refresh(db_cliente)
    return db_cliente


@app.delete("/api/clientes/{cliente_id}")
def excluir_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Exclui um cliente (soft delete)"""
    db_cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    db_cliente.ativo = False
    db.commit()
    return {"message": "Cliente excluido com sucesso"}


# ============== API: Enderecos ==============

@app.get("/api/clientes/{cliente_id}/enderecos", response_model=List[EnderecoResponse])
def listar_enderecos(cliente_id: int, ativo: bool = True, db: Session = Depends(get_db)):
    """Lista enderecos de um cliente"""
    query = db.query(Endereco).filter(Endereco.cliente_id == cliente_id)
    if ativo:
        query = query.filter(Endereco.ativo == True)
    return query.all()


@app.post("/api/clientes/{cliente_id}/enderecos", response_model=EnderecoResponse)
def criar_endereco(cliente_id: int, endereco: EnderecoCreate, db: Session = Depends(get_db)):
    """Cria um novo endereco para um cliente"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    if endereco.principal:
        db.query(Endereco).filter(
            Endereco.cliente_id == cliente_id,
            Endereco.principal == True
        ).update({Endereco.principal: False})

    db_endereco = Endereco(cliente_id=cliente_id, **endereco.model_dump())
    db.add(db_endereco)
    db.commit()
    db.refresh(db_endereco)
    return db_endereco


@app.put("/api/enderecos/{endereco_id}", response_model=EnderecoResponse)
def atualizar_endereco(endereco_id: int, endereco: EnderecoUpdate, db: Session = Depends(get_db)):
    """Atualiza um endereco"""
    db_endereco = db.query(Endereco).filter(Endereco.id == endereco_id).first()
    if not db_endereco:
        raise HTTPException(status_code=404, detail="Endereco nao encontrado")

    if endereco.principal:
        db.query(Endereco).filter(
            Endereco.cliente_id == db_endereco.cliente_id,
            Endereco.id != endereco_id,
            Endereco.principal == True
        ).update({Endereco.principal: False})

    update_data = endereco.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_endereco, key, value)

    db.commit()
    db.refresh(db_endereco)
    return db_endereco


@app.delete("/api/enderecos/{endereco_id}")
def excluir_endereco(endereco_id: int, db: Session = Depends(get_db)):
    """Exclui um endereco (soft delete)"""
    db_endereco = db.query(Endereco).filter(Endereco.id == endereco_id).first()
    if not db_endereco:
        raise HTTPException(status_code=404, detail="Endereco nao encontrado")

    db_endereco.ativo = False
    db.commit()
    return {"message": "Endereco excluido com sucesso"}


# ============== API: Impressoras ==============

@app.get("/api/impressoras/sistema")
def listar_impressoras_sistema():
    """Lista impressoras disponiveis no sistema operacional"""
    return printer_service.list_printers()


@app.get("/api/impressoras", response_model=List[ImpressoraResponse])
def listar_impressoras(ativa: bool = True, db: Session = Depends(get_db)):
    """Lista impressoras cadastradas"""
    query = db.query(Impressora)
    if ativa:
        query = query.filter(Impressora.ativa == True)
    return query.all()


@app.post("/api/impressoras", response_model=ImpressoraResponse)
def criar_impressora(impressora: ImpressoraCreate, db: Session = Depends(get_db)):
    """Cadastra uma nova impressora"""
    db_impressora = Impressora(**impressora.model_dump())
    db.add(db_impressora)
    db.commit()
    db.refresh(db_impressora)
    return db_impressora


@app.put("/api/impressoras/{impressora_id}", response_model=ImpressoraResponse)
def atualizar_impressora(impressora_id: int, impressora: ImpressoraUpdate, db: Session = Depends(get_db)):
    """Atualiza uma impressora"""
    db_impressora = db.query(Impressora).filter(Impressora.id == impressora_id).first()
    if not db_impressora:
        raise HTTPException(status_code=404, detail="Impressora nao encontrada")

    update_data = impressora.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_impressora, key, value)

    db.commit()
    db.refresh(db_impressora)
    return db_impressora


@app.delete("/api/impressoras/{impressora_id}")
def excluir_impressora(impressora_id: int, db: Session = Depends(get_db)):
    """Exclui uma impressora"""
    db_impressora = db.query(Impressora).filter(Impressora.id == impressora_id).first()
    if not db_impressora:
        raise HTTPException(status_code=404, detail="Impressora nao encontrada")

    db_impressora.ativa = False
    db.commit()
    return {"message": "Impressora excluida com sucesso"}


@app.get("/api/impressoras/{impressora_id}/testar")
def testar_impressora(impressora_id: int, db: Session = Depends(get_db)):
    """Testa uma impressora"""
    db_impressora = db.query(Impressora).filter(Impressora.id == impressora_id).first()
    if not db_impressora:
        raise HTTPException(status_code=404, detail="Impressora nao encontrada")

    success = printer_service.test_printer(db_impressora.nome_sistema)
    return {"success": success, "message": "Impressora OK" if success else "Impressora nao responde"}


# ============== API: Configuracoes de Etiquetas ==============

@app.get("/api/tipos-etiqueta")
def listar_tipos_etiqueta():
    """Lista todos os tipos de etiqueta disponiveis"""
    tipos = [
        {"id": key, **value}
        for key, value in LABEL_SIZES.items()
    ]
    # Adicionar tipo Pimaco 6 por folha (padrao Correios)
    tipos.append({
        "id": "pimaco_6",
        "width": 101.6,
        "height": 84.7,
        "name": "Pimaco 6184 (84,7x101,6mm - 6/folha)"
    })
    return tipos


@app.get("/api/configuracoes-etiqueta", response_model=List[ConfiguracaoEtiquetaResponse])
def listar_configuracoes_etiqueta(db: Session = Depends(get_db)):
    """Lista configuracoes de impressora por tipo de etiqueta"""
    return db.query(ConfiguracaoEtiqueta).all()


@app.put("/api/configuracoes-etiqueta/{tipo_etiqueta}")
def atualizar_configuracao_etiqueta(
    tipo_etiqueta: str,
    impressora_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Define a impressora padrao para um tipo de etiqueta"""
    config = db.query(ConfiguracaoEtiqueta).filter(
        ConfiguracaoEtiqueta.tipo_etiqueta == tipo_etiqueta
    ).first()

    if not config:
        config = ConfiguracaoEtiqueta(tipo_etiqueta=tipo_etiqueta)
        db.add(config)

    config.impressora_id = impressora_id
    db.commit()
    db.refresh(config)
    return {"message": "Configuracao atualizada", "config": config}


# ============== API: Impressao ==============

@app.post("/api/preview")
def gerar_preview(request: ImpressaoPreviewRequest, db: Session = Depends(get_db)):
    """Gera preview da etiqueta em PDF"""
    cliente = db.query(Cliente).filter(Cliente.id == request.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    endereco = db.query(Endereco).filter(
        Endereco.id == request.endereco_id,
        Endereco.cliente_id == request.cliente_id
    ).first()
    if not endereco:
        raise HTTPException(status_code=404, detail="Endereco nao encontrado")

    endereco_dict = {
        "destinatario": endereco.destinatario,
        "logradouro": endereco.logradouro,
        "numero": endereco.numero,
        "complemento": endereco.complemento,
        "bairro": endereco.bairro,
        "cidade": endereco.cidade,
        "estado": endereco.estado,
        "cep": endereco.cep
    }

    # Carregar remetente se necessario
    if request.incluir_remetente:
        remetente = system_settings.get_remetente()
        if remetente and remetente.get('nome'):
            label_generator.set_remetente(remetente)

    pdf_content = label_generator.generate_label(
        cliente.nome,
        endereco_dict,
        request.tipo_etiqueta,
        request.incluir_codigo_barras,
        request.incluir_remetente
    )

    return StreamingResponse(
        io.BytesIO(pdf_content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=preview_{request.tipo_etiqueta}.pdf"}
    )


@app.post("/api/imprimir")
def imprimir_etiqueta(request: ImpressaoRequest, db: Session = Depends(get_db)):
    """Imprime a etiqueta"""
    cliente = db.query(Cliente).filter(Cliente.id == request.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    endereco = db.query(Endereco).filter(
        Endereco.id == request.endereco_id,
        Endereco.cliente_id == request.cliente_id
    ).first()
    if not endereco:
        raise HTTPException(status_code=404, detail="Endereco nao encontrado")

    impressora_id = request.impressora_id
    if not impressora_id:
        config = db.query(ConfiguracaoEtiqueta).filter(
            ConfiguracaoEtiqueta.tipo_etiqueta == request.tipo_etiqueta
        ).first()
        if config and config.impressora_id:
            impressora_id = config.impressora_id

    if not impressora_id:
        raise HTTPException(status_code=400, detail="Nenhuma impressora configurada para este tipo de etiqueta")

    impressora = db.query(Impressora).filter(Impressora.id == impressora_id).first()
    if not impressora:
        raise HTTPException(status_code=404, detail="Impressora nao encontrada")

    endereco_dict = {
        "destinatario": endereco.destinatario,
        "logradouro": endereco.logradouro,
        "numero": endereco.numero,
        "complemento": endereco.complemento,
        "bairro": endereco.bairro,
        "cidade": endereco.cidade,
        "estado": endereco.estado,
        "cep": endereco.cep
    }

    if request.incluir_remetente:
        remetente = system_settings.get_remetente()
        if remetente and remetente.get('nome'):
            label_generator.set_remetente(remetente)

    pdf_content = label_generator.generate_label(
        cliente.nome,
        endereco_dict,
        request.tipo_etiqueta,
        request.incluir_codigo_barras,
        request.incluir_remetente
    )

    success = printer_service.print_label(
        pdf_content,
        impressora.nome_sistema,
        request.tipo_etiqueta,
        request.quantidade
    )

    if not success:
        raise HTTPException(status_code=500, detail="Erro ao enviar para impressora")

    historico = HistoricoImpressao(
        cliente_id=request.cliente_id,
        endereco_id=request.endereco_id,
        tipo_etiqueta=request.tipo_etiqueta,
        impressora_id=impressora_id,
        quantidade=request.quantidade
    )
    db.add(historico)
    db.commit()

    return {"message": "Etiqueta enviada para impressao", "success": True}


@app.post("/api/download")
def download_etiqueta(request: ImpressaoPreviewRequest, db: Session = Depends(get_db)):
    """Faz download do PDF da etiqueta"""
    cliente = db.query(Cliente).filter(Cliente.id == request.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    endereco = db.query(Endereco).filter(
        Endereco.id == request.endereco_id,
        Endereco.cliente_id == request.cliente_id
    ).first()
    if not endereco:
        raise HTTPException(status_code=404, detail="Endereco nao encontrado")

    endereco_dict = {
        "destinatario": endereco.destinatario,
        "logradouro": endereco.logradouro,
        "numero": endereco.numero,
        "complemento": endereco.complemento,
        "bairro": endereco.bairro,
        "cidade": endereco.cidade,
        "estado": endereco.estado,
        "cep": endereco.cep
    }

    if request.incluir_remetente:
        remetente = system_settings.get_remetente()
        if remetente and remetente.get('nome'):
            label_generator.set_remetente(remetente)

    pdf_content = label_generator.generate_label(
        cliente.nome,
        endereco_dict,
        request.tipo_etiqueta,
        request.incluir_codigo_barras,
        request.incluir_remetente
    )

    filename = f"etiqueta_{cliente.nome.replace(' ', '_')}_{request.tipo_etiqueta}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============== API: Remetente (legado - redireciona para settings) ==============

@app.get("/api/remetente")
def obter_remetente():
    """Obtem configuracao do remetente"""
    return system_settings.get_remetente()


@app.post("/api/remetente")
def salvar_remetente(remetente: RemetenteConfig):
    """Salva configuracao do remetente"""
    system_settings.set_remetente(remetente.model_dump())
    label_generator.set_remetente(remetente.model_dump())
    return {"message": "Remetente salvo com sucesso"}


# ============== API: Historico ==============

@app.get("/api/historico", response_model=List[HistoricoImpressaoResponse])
def listar_historico(
    skip: int = 0,
    limit: int = 50,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Lista historico de impressoes"""
    query = db.query(HistoricoImpressao)

    if cliente_id:
        query = query.filter(HistoricoImpressao.cliente_id == cliente_id)

    historicos = query.order_by(HistoricoImpressao.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for h in historicos:
        result.append({
            "id": h.id,
            "cliente_id": h.cliente_id,
            "endereco_id": h.endereco_id,
            "tipo_etiqueta": h.tipo_etiqueta,
            "quantidade": h.quantidade,
            "created_at": h.created_at,
            "cliente_nome": h.cliente.nome if h.cliente else None,
            "endereco_descricao": h.endereco.descricao if h.endereco else None
        })

    return result


# ============== Inicializacao ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
