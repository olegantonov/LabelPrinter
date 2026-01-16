"""
API Principal do Sistema de Impressao de Etiquetas
Integracoes: BrasilAPI (CEP), Benu ERP
Padrao: Correios (CEPNet, Data Matrix)
Apenas etiquetas termicas
"""
from fastapi import FastAPI, Depends, HTTPException, Query, Response, Body, BackgroundTasks
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
import asyncio

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
from services.updater_service import updater_service

# Inicializar aplicacao
app = FastAPI(
    title="Sistema de Impressao de Etiquetas",
    description="API para impressao de etiquetas termicas com integracao Benu ERP",
    version="3.0.0"
)

# Configurar arquivos estaticos e templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend/static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend/templates"))


# ============== Schemas Adicionais ==============

class BenuTokenUpdate(BaseModel):
    token: str

class EtiquetaConfigUpdate(BaseModel):
    resolucao_dpi: int = 300
    tamanho_fonte_min: int = 10
    incluir_cepnet: bool = True
    incluir_datamatrix: bool = False

class DataMatrixConfigUpdate(BaseModel):
    idv_padrao: str = "03"
    cnae: str = ""

class ImpressaoDiretaRequest(BaseModel):
    """Impressao direta com dados do Benu (sem salvar no DB)"""
    nome: str
    logradouro: str
    numero: str
    complemento: Optional[str] = ""
    bairro: str
    cidade: str
    estado: str
    cep: str
    destinatario: Optional[str] = None
    tipo_etiqueta: str = "thermal_60x30"
    quantidade: int = 1
    impressora_id: Optional[int] = None
    incluir_codigo_barras: bool = True
    incluir_remetente: bool = False

class BenuSearchRequest(BaseModel):
    termo: Optional[str] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    tipo: str = "os"  # os, orcamentos, crm


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

    # Iniciar verificacao automatica de atualizacoes
    asyncio.create_task(updater_service.auto_update_loop())


# ============== Frontend Routes ==============

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Pagina inicial"""
    return templates.TemplateResponse("index.html", {"request": request})


# ============== API: Consulta de CEP (BrasilAPI) ==============

@app.get("/api/cep/{cep}")
async def consultar_cep(cep: str):
    """Consulta CEP via BrasilAPI com cache de 30 dias"""
    if not cep_service.validate_cep(cep):
        raise HTTPException(status_code=400, detail="CEP invalido. Deve conter 8 digitos.")

    resultado = await cep_service.fetch_cep_v1(cep)

    if resultado is None:
        raise HTTPException(status_code=404, detail="CEP nao encontrado")

    return cep_service.map_to_address(resultado)


# ============== API: Benu ERP - Busca de Dados ==============

@app.get("/api/benu/status")
async def benu_status():
    """Verifica status da conexao com Benu ERP"""
    if not benu_service.token:
        return {"connected": False, "message": "Token nao configurado"}

    result = await benu_service.test_connection()
    return {
        "connected": result.get("success", False),
        "message": result.get("message", "")
    }

@app.post("/api/benu/buscar")
async def benu_buscar(request: BenuSearchRequest):
    """
    Busca dados no Benu ERP
    Tipos: os (Ordem de Servico), orcamentos, crm
    """
    if not benu_service.token:
        raise HTTPException(status_code=400, detail="Token Benu nao configurado")

    if request.tipo == "os":
        result = await benu_service.buscar_os(
            termo=request.termo,
            data_inicio=request.data_inicio,
            data_fim=request.data_fim
        )
    elif request.tipo == "orcamentos":
        result = await benu_service.buscar_orcamentos(
            termo=request.termo,
            data_inicio=request.data_inicio,
            data_fim=request.data_fim
        )
    elif request.tipo == "crm":
        result = await benu_service.consultar_cards_crm(
            termo_busca=request.termo
        )
    else:
        raise HTTPException(status_code=400, detail="Tipo de busca invalido")

    if result.get("error"):
        raise HTTPException(
            status_code=result.get("code", 500),
            detail=result.get("message")
        )

    return result.get("data", [])

@app.get("/api/benu/os")
async def benu_listar_os(
    termo: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """Lista Ordens de Servico do Benu ERP"""
    result = await benu_service.buscar_os(
        termo=termo,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    if result.get("error"):
        raise HTTPException(status_code=result.get("code", 500), detail=result.get("message"))
    return result.get("data", [])

@app.get("/api/benu/orcamentos")
async def benu_listar_orcamentos(
    termo: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """Lista Orcamentos do Benu ERP"""
    result = await benu_service.buscar_orcamentos(
        termo=termo,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    if result.get("error"):
        raise HTTPException(status_code=result.get("code", 500), detail=result.get("message"))
    return result.get("data", [])

@app.get("/api/benu/crm")
async def benu_listar_crm(
    termo: Optional[str] = None,
    funil: int = 1,
    offset: int = 0,
    limite: int = 100
):
    """Lista Cards do CRM do Benu ERP"""
    result = await benu_service.consultar_cards_crm(
        cd_funil=funil,
        offset=offset,
        max_results=limite,
        termo_busca=termo
    )
    if result.get("error"):
        raise HTTPException(status_code=result.get("code", 500), detail=result.get("message"))
    return result.get("data", [])


# ============== API: Configuracoes do Sistema ==============

@app.get("/api/settings")
def obter_configuracoes():
    """Retorna todas as configuracoes do sistema"""
    return system_settings.get_all()

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

@app.post("/api/settings/etiquetas")
def atualizar_config_etiquetas(config: EtiquetaConfigUpdate):
    """Atualiza configuracoes de etiqueta"""
    data = config.model_dump()
    system_settings.update("etiquetas", data)
    label_generator.set_config(data)
    return {"message": "Configuracoes de etiqueta atualizadas"}

@app.post("/api/settings/datamatrix")
def atualizar_config_datamatrix(config: DataMatrixConfigUpdate):
    """Atualiza configuracoes de Data Matrix"""
    system_settings.update("datamatrix", config.model_dump())
    return {"message": "Configuracoes de Data Matrix atualizadas"}


# ============== API: Sistema de Atualizacao ==============

@app.get("/api/system/version")
def obter_versao():
    """Retorna versao atual do sistema"""
    return updater_service.get_current_version()

@app.get("/api/system/update/status")
def status_atualizacao():
    """Retorna status do sistema de atualizacao"""
    return updater_service.get_status()

@app.get("/api/system/update/check")
def verificar_atualizacao():
    """Verifica se ha atualizacoes disponiveis"""
    return updater_service.check_for_updates()

@app.get("/api/system/debug")
def debug_sistema():
    """Retorna informacoes de debug do sistema"""
    import os
    return {
        "updater_status": updater_service.get_status(),
        "benu_token_configured": bool(benu_service.token),
        "benu_base_url": benu_service.BASE_URL,
        "cwd": os.getcwd(),
        "env_path": os.environ.get("PATH", "")[:200]
    }

@app.post("/api/system/update/apply")
def aplicar_atualizacao():
    """Aplica atualizacoes disponiveis (requer reinicio)"""
    result = updater_service.apply_update()
    return result


# ============== API: Impressao Direta (Benu) ==============

@app.post("/api/imprimir/direto")
def imprimir_direto(request: ImpressaoDiretaRequest, db: Session = Depends(get_db)):
    """
    Imprime etiqueta diretamente com dados informados (sem salvar cliente no DB)
    Use para dados vindos do Benu ERP
    """
    # Verificar tipo de etiqueta
    if request.tipo_etiqueta not in LABEL_SIZES:
        raise HTTPException(status_code=400, detail="Tipo de etiqueta invalido")

    # Buscar impressora
    impressora_id = request.impressora_id
    if not impressora_id:
        config = db.query(ConfiguracaoEtiqueta).filter(
            ConfiguracaoEtiqueta.tipo_etiqueta == request.tipo_etiqueta
        ).first()
        if config and config.impressora_id:
            impressora_id = config.impressora_id

    if not impressora_id:
        raise HTTPException(status_code=400, detail="Nenhuma impressora configurada")

    impressora = db.query(Impressora).filter(Impressora.id == impressora_id).first()
    if not impressora:
        raise HTTPException(status_code=404, detail="Impressora nao encontrada")

    # Montar endereco
    endereco_dict = {
        "destinatario": request.destinatario,
        "logradouro": request.logradouro,
        "numero": request.numero,
        "complemento": request.complemento,
        "bairro": request.bairro,
        "cidade": request.cidade,
        "estado": request.estado,
        "cep": request.cep
    }

    # Carregar remetente se necessario
    if request.incluir_remetente:
        remetente = system_settings.get_remetente()
        if remetente and remetente.get('nome'):
            label_generator.set_remetente(remetente)

    # Gerar PDF
    pdf_content = label_generator.generate_label(
        request.nome,
        endereco_dict,
        request.tipo_etiqueta,
        request.incluir_codigo_barras,
        request.incluir_remetente
    )

    # Imprimir
    success = printer_service.print_label(
        pdf_content,
        impressora.nome_sistema,
        request.tipo_etiqueta,
        request.quantidade
    )

    if not success:
        raise HTTPException(status_code=500, detail="Erro ao enviar para impressora")

    return {"message": "Etiqueta enviada para impressao", "success": True}


@app.post("/api/preview/direto")
def preview_direto(request: ImpressaoDiretaRequest):
    """Gera preview da etiqueta com dados informados diretamente"""
    if request.tipo_etiqueta not in LABEL_SIZES:
        raise HTTPException(status_code=400, detail="Tipo de etiqueta invalido")

    endereco_dict = {
        "destinatario": request.destinatario,
        "logradouro": request.logradouro,
        "numero": request.numero,
        "complemento": request.complemento,
        "bairro": request.bairro,
        "cidade": request.cidade,
        "estado": request.estado,
        "cep": request.cep
    }

    if request.incluir_remetente:
        remetente = system_settings.get_remetente()
        if remetente and remetente.get('nome'):
            label_generator.set_remetente(remetente)

    pdf_content = label_generator.generate_label(
        request.nome,
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


@app.post("/api/download/direto")
def download_direto(request: ImpressaoDiretaRequest):
    """Download da etiqueta com dados informados diretamente"""
    if request.tipo_etiqueta not in LABEL_SIZES:
        raise HTTPException(status_code=400, detail="Tipo de etiqueta invalido")

    endereco_dict = {
        "destinatario": request.destinatario,
        "logradouro": request.logradouro,
        "numero": request.numero,
        "complemento": request.complemento,
        "bairro": request.bairro,
        "cidade": request.cidade,
        "estado": request.estado,
        "cep": request.cep
    }

    if request.incluir_remetente:
        remetente = system_settings.get_remetente()
        if remetente and remetente.get('nome'):
            label_generator.set_remetente(remetente)

    pdf_content = label_generator.generate_label(
        request.nome,
        endereco_dict,
        request.tipo_etiqueta,
        request.incluir_codigo_barras,
        request.incluir_remetente
    )

    filename = f"etiqueta_{request.nome.replace(' ', '_')}_{request.tipo_etiqueta}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


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
    """Lista todos os tipos de etiqueta disponiveis (apenas termicas)"""
    return [{"id": key, **value} for key, value in LABEL_SIZES.items()]

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


# ============== API: Remetente ==============

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


# ============== Inicializacao ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
