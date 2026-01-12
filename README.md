# Sistema de Impressao de Etiquetas

Sistema web para gerenciamento e impressao de etiquetas de endereco com suporte a codigo de barras no padrao dos Correios.

## Funcionalidades

- Cadastro de clientes e multiplos enderecos
- Impressao de etiquetas em diversos formatos:
  - Termica 60x30mm
  - Termica 100x80mm
  - Pimaco A4 (38,1x99mm - 14 etiquetas por folha)
  - Envelope DL (110x220mm)
  - Envelope C5 (162x229mm)
- Codigo de barras no padrao dos Correios (CEP + digito verificador)
- Configuracao de impressora padrao por tipo de etiqueta
- Dados do remetente configuravel
- Preview e download de etiquetas em PDF
- Historico de impressoes

## Requisitos

- Python 3.9+
- CUPS (para impressao no Linux)

## Instalacao

### Opcao 1: Script de Inicializacao

```bash
# Clonar repositorio
git clone <url-do-repositorio>
cd LabelPrinter

# Executar script
./run.sh
```

### Opcao 2: Manual

```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
cd backend
pip install -r requirements.txt

# Iniciar servidor
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Opcao 3: Docker

```bash
# Construir e iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f
```

## Acesso

Apos iniciar, acesse: http://localhost:8000

## Configuracao de Impressoras

1. Acesse a aba "Impressoras"
2. Clique em "Detectar do Sistema" para listar impressoras CUPS
3. Adicione as impressoras desejadas
4. Na aba "Configuracoes", defina a impressora padrao para cada tipo de etiqueta

### Configurando CUPS no Linux

```bash
# Instalar CUPS
sudo apt-get install cups

# Adicionar usuario ao grupo lpadmin
sudo usermod -a -G lpadmin $USER

# Acessar interface web do CUPS
# http://localhost:631
```

## Uso

### Impressao de Etiquetas

1. Selecione o cliente
2. Escolha o endereco
3. Selecione o tipo de etiqueta
4. Opcionalmente, escolha uma impressora especifica
5. Defina a quantidade
6. Marque/desmarque opcoes (codigo de barras, remetente)
7. Clique em "Visualizar" para preview ou "Imprimir" para enviar

### Cadastro de Clientes

1. Acesse a aba "Clientes"
2. Clique em "Novo Cliente"
3. Preencha os dados e adicione enderecos
4. Salve

### Configuracao do Remetente

1. Acesse a aba "Configuracoes"
2. Preencha os dados do remetente
3. Salve
4. Marque "Incluir remetente" na impressao

## Estrutura do Projeto

```
LabelPrinter/
├── backend/
│   ├── main.py              # API FastAPI
│   ├── models.py            # Modelos SQLAlchemy
│   ├── schemas.py           # Schemas Pydantic
│   ├── database.py          # Configuracao do banco
│   ├── config.py            # Configuracoes
│   ├── label_generator.py   # Geracao de etiquetas/PDF
│   ├── printer_service.py   # Integracao com CUPS
│   └── requirements.txt     # Dependencias Python
├── frontend/
│   ├── templates/
│   │   └── index.html       # Pagina principal
│   └── static/
│       ├── css/style.css    # Estilos
│       └── js/app.js        # JavaScript
├── docker-compose.yml       # Configuracao Docker
├── Dockerfile
├── run.sh                   # Script de inicializacao
└── README.md
```

## API Endpoints

### Clientes
- `GET /api/clientes` - Listar clientes
- `POST /api/clientes` - Criar cliente
- `GET /api/clientes/{id}` - Obter cliente
- `PUT /api/clientes/{id}` - Atualizar cliente
- `DELETE /api/clientes/{id}` - Excluir cliente

### Enderecos
- `GET /api/clientes/{id}/enderecos` - Listar enderecos
- `POST /api/clientes/{id}/enderecos` - Criar endereco
- `PUT /api/enderecos/{id}` - Atualizar endereco
- `DELETE /api/enderecos/{id}` - Excluir endereco

### Impressoras
- `GET /api/impressoras/sistema` - Listar impressoras do sistema
- `GET /api/impressoras` - Listar impressoras cadastradas
- `POST /api/impressoras` - Criar impressora
- `PUT /api/impressoras/{id}` - Atualizar impressora
- `GET /api/impressoras/{id}/testar` - Testar impressora

### Impressao
- `POST /api/preview` - Gerar preview PDF
- `POST /api/download` - Download PDF
- `POST /api/imprimir` - Enviar para impressora

### Configuracoes
- `GET /api/tipos-etiqueta` - Listar tipos de etiqueta
- `GET /api/configuracoes-etiqueta` - Listar configuracoes
- `PUT /api/configuracoes-etiqueta/{tipo}` - Atualizar configuracao
- `GET /api/remetente` - Obter remetente
- `POST /api/remetente` - Salvar remetente

## Codigo de Barras dos Correios

O sistema gera codigos de barras no formato Code128 contendo:
- 8 digitos do CEP
- 1 digito verificador (modulo 10)

Este formato e compativel com os sistemas de leitura dos Correios.

## Licenca

MIT License
