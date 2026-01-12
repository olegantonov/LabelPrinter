"""
API Principal do Sistema de Impressão de Etiquetas
"""
from fastapi import FastAPI, Depends, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
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

# Inicializar aplicação
app = FastAPI(
    title="Sistema de Impressão de Etiquetas",
    description="API para gerenciamento e impressão de etiquetas de endereço",
    version="1.0.0"
)

# Configurar arquivos estáticos e templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend/static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend/templates"))


# ============== Eventos de Startup ==============

@app.on_event("startup")
async def startup_event():
    """Inicializa o banco de dados na inicialização"""
    init_db()

    # Criar configurações padrão para tipos de etiqueta
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


# ============== Frontend Routes ==============

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Página inicial"""
    return templates.TemplateResponse("index.html", {"request": request})


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

    # Adicionar contagem de endereços
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
    """Obtém um cliente específico com seus endereços"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
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

    # Adicionar endereços se fornecidos
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
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

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
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    db_cliente.ativo = False
    db.commit()
    return {"message": "Cliente excluído com sucesso"}


# ============== API: Endereços ==============

@app.get("/api/clientes/{cliente_id}/enderecos", response_model=List[EnderecoResponse])
def listar_enderecos(cliente_id: int, ativo: bool = True, db: Session = Depends(get_db)):
    """Lista endereços de um cliente"""
    query = db.query(Endereco).filter(Endereco.cliente_id == cliente_id)
    if ativo:
        query = query.filter(Endereco.ativo == True)
    return query.all()


@app.post("/api/clientes/{cliente_id}/enderecos", response_model=EnderecoResponse)
def criar_endereco(cliente_id: int, endereco: EnderecoCreate, db: Session = Depends(get_db)):
    """Cria um novo endereço para um cliente"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Se for endereço principal, desmarcar outros
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
    """Atualiza um endereço"""
    db_endereco = db.query(Endereco).filter(Endereco.id == endereco_id).first()
    if not db_endereco:
        raise HTTPException(status_code=404, detail="Endereço não encontrado")

    # Se estiver marcando como principal, desmarcar outros
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
    """Exclui um endereço (soft delete)"""
    db_endereco = db.query(Endereco).filter(Endereco.id == endereco_id).first()
    if not db_endereco:
        raise HTTPException(status_code=404, detail="Endereço não encontrado")

    db_endereco.ativo = False
    db.commit()
    return {"message": "Endereço excluído com sucesso"}


# ============== API: Impressoras ==============

@app.get("/api/impressoras/sistema")
def listar_impressoras_sistema():
    """Lista impressoras disponíveis no sistema operacional"""
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
        raise HTTPException(status_code=404, detail="Impressora não encontrada")

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
        raise HTTPException(status_code=404, detail="Impressora não encontrada")

    db_impressora.ativa = False
    db.commit()
    return {"message": "Impressora excluída com sucesso"}


@app.get("/api/impressoras/{impressora_id}/testar")
def testar_impressora(impressora_id: int, db: Session = Depends(get_db)):
    """Testa uma impressora"""
    db_impressora = db.query(Impressora).filter(Impressora.id == impressora_id).first()
    if not db_impressora:
        raise HTTPException(status_code=404, detail="Impressora não encontrada")

    success = printer_service.test_printer(db_impressora.nome_sistema)
    return {"success": success, "message": "Impressora OK" if success else "Impressora não responde"}


# ============== API: Configurações de Etiquetas ==============

@app.get("/api/tipos-etiqueta")
def listar_tipos_etiqueta():
    """Lista todos os tipos de etiqueta disponíveis"""
    return [
        {"id": key, **value}
        for key, value in LABEL_SIZES.items()
    ]


@app.get("/api/configuracoes-etiqueta", response_model=List[ConfiguracaoEtiquetaResponse])
def listar_configuracoes_etiqueta(db: Session = Depends(get_db)):
    """Lista configurações de impressora por tipo de etiqueta"""
    return db.query(ConfiguracaoEtiqueta).all()


@app.put("/api/configuracoes-etiqueta/{tipo_etiqueta}")
def atualizar_configuracao_etiqueta(
    tipo_etiqueta: str,
    impressora_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Define a impressora padrão para um tipo de etiqueta"""
    config = db.query(ConfiguracaoEtiqueta).filter(
        ConfiguracaoEtiqueta.tipo_etiqueta == tipo_etiqueta
    ).first()

    if not config:
        config = ConfiguracaoEtiqueta(tipo_etiqueta=tipo_etiqueta)
        db.add(config)

    config.impressora_id = impressora_id
    db.commit()
    db.refresh(config)
    return {"message": "Configuração atualizada", "config": config}


# ============== API: Impressão ==============

@app.post("/api/preview")
def gerar_preview(request: ImpressaoPreviewRequest, db: Session = Depends(get_db)):
    """Gera preview da etiqueta em PDF"""
    # Buscar cliente e endereço
    cliente = db.query(Cliente).filter(Cliente.id == request.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    endereco = db.query(Endereco).filter(
        Endereco.id == request.endereco_id,
        Endereco.cliente_id == request.cliente_id
    ).first()
    if not endereco:
        raise HTTPException(status_code=404, detail="Endereço não encontrado")

    # Preparar dados do endereço
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

    # Gerar PDF
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
    # Buscar cliente e endereço
    cliente = db.query(Cliente).filter(Cliente.id == request.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    endereco = db.query(Endereco).filter(
        Endereco.id == request.endereco_id,
        Endereco.cliente_id == request.cliente_id
    ).first()
    if not endereco:
        raise HTTPException(status_code=404, detail="Endereço não encontrado")

    # Determinar impressora
    impressora_id = request.impressora_id
    if not impressora_id:
        # Buscar impressora configurada para o tipo
        config = db.query(ConfiguracaoEtiqueta).filter(
            ConfiguracaoEtiqueta.tipo_etiqueta == request.tipo_etiqueta
        ).first()
        if config and config.impressora_id:
            impressora_id = config.impressora_id

    if not impressora_id:
        raise HTTPException(status_code=400, detail="Nenhuma impressora configurada para este tipo de etiqueta")

    impressora = db.query(Impressora).filter(Impressora.id == impressora_id).first()
    if not impressora:
        raise HTTPException(status_code=404, detail="Impressora não encontrada")

    # Preparar dados do endereço
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

    # Gerar PDF
    pdf_content = label_generator.generate_label(
        cliente.nome,
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

    # Registrar no histórico
    historico = HistoricoImpressao(
        cliente_id=request.cliente_id,
        endereco_id=request.endereco_id,
        tipo_etiqueta=request.tipo_etiqueta,
        impressora_id=impressora_id,
        quantidade=request.quantidade
    )
    db.add(historico)
    db.commit()

    return {"message": "Etiqueta enviada para impressão", "success": True}


@app.post("/api/download")
def download_etiqueta(request: ImpressaoPreviewRequest, db: Session = Depends(get_db)):
    """Faz download do PDF da etiqueta"""
    # Buscar cliente e endereço
    cliente = db.query(Cliente).filter(Cliente.id == request.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    endereco = db.query(Endereco).filter(
        Endereco.id == request.endereco_id,
        Endereco.cliente_id == request.cliente_id
    ).first()
    if not endereco:
        raise HTTPException(status_code=404, detail="Endereço não encontrado")

    # Preparar dados do endereço
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

    # Gerar PDF
    pdf_content = label_generator.generate_label(
        cliente.nome,
        endereco_dict,
        request.tipo_etiqueta,
        request.incluir_codigo_barras,
        request.incluir_remetente
    )

    # Nome do arquivo
    filename = f"etiqueta_{cliente.nome.replace(' ', '_')}_{request.tipo_etiqueta}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============== API: Remetente ==============

@app.get("/api/remetente")
def obter_remetente():
    """Obtém configuração do remetente"""
    config_path = os.path.join(settings.UPLOAD_DIR, "remetente.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return None


@app.post("/api/remetente")
def salvar_remetente(remetente: RemetenteConfig):
    """Salva configuração do remetente"""
    config_path = os.path.join(settings.UPLOAD_DIR, "remetente.json")
    with open(config_path, 'w') as f:
        json.dump(remetente.model_dump(), f, ensure_ascii=False, indent=2)

    # Atualizar gerador de etiquetas
    label_generator.set_remetente(remetente.model_dump())

    return {"message": "Remetente salvo com sucesso"}


# ============== API: Histórico ==============

@app.get("/api/historico", response_model=List[HistoricoImpressaoResponse])
def listar_historico(
    skip: int = 0,
    limit: int = 50,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Lista histórico de impressões"""
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


# ============== Inicialização ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
