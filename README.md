# Sistema de Impressao de Etiquetas

Sistema web para gerenciamento e impressao de etiquetas de endereco com suporte a codigo de barras no padrao dos Correios, integracao com BrasilAPI (CEP) e Benu ERP.

## Funcionalidades

### Tipos de Etiquetas
- Termica 60x30mm
- Termica 100x80mm
- Pimaco A4 38,1x99mm (14 etiquetas por folha)
- Pimaco 6184 84,7x101,6mm (6 etiquetas por folha) - Padrao Correios
- Envelope DL (110x220mm)
- Envelope C5 (162x229mm)

### Recursos
- Cadastro de clientes e multiplos enderecos
- Selecao de cliente e endereco para impressao
- **Busca automatica de CEP via BrasilAPI** (com cache de 30 dias)
- **Codigo de barras CEPNet** (padrao Correios - 8 digitos + verificador)
- **Data Matrix** conforme especificacao Correios
- Configuracao de impressora padrao por tipo de etiqueta
- Dados do remetente configuravel
- Preview e download de etiquetas em PDF
- Integracao com CUPS para impressao direta no Linux
- **Integracao com Benu ERP** (autenticacao Bearer Token)

### Padrao Correios Implementado
- CEPNet: codigo de barras do CEP (47 barras)
- Data Matrix: codigo 2D para triagem automatizada
- Layouts conforme Areas 1-6 dos Correios
- Resolucao minima: 300 DPI
- Fonte minima: 10 pontos

---

## Passo a Passo - Instalacao no Servidor Linux

### 1. Requisitos do Sistema

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python 3.9+
sudo apt install python3 python3-pip python3-venv -y

# Instalar CUPS (sistema de impressao)
sudo apt install cups cups-client -y

# Instalar Git
sudo apt install git -y
```

### 2. Clonar o Repositorio

```bash
# Criar diretorio para aplicacao
sudo mkdir -p /opt/labelprinter
sudo chown $USER:$USER /opt/labelprinter

# Clonar repositorio
cd /opt/labelprinter
git clone https://github.com/olegantonov/LabelPrinter.git .
```

### 3. Configurar Ambiente Python

```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente
source venv/bin/activate

# Instalar dependencias
cd backend
pip install -r requirements.txt
```

### 4. Criar Diretorios Necessarios

```bash
mkdir -p uploads generated_labels cache config
```

### 5. Configurar Variaveis de Ambiente (Opcional)

```bash
# Copiar arquivo de exemplo
cp ../.env.example .env

# Editar conforme necessario
nano .env
```

Conteudo do `.env`:
```
DATABASE_URL=sqlite:///./labelprinter.db
HOST=0.0.0.0
PORT=8000
DEBUG=False
UPLOAD_DIR=./uploads
LABELS_DIR=./generated_labels
```

### 6. Testar Execucao Manual

```bash
# Ativar ambiente virtual
source /opt/labelprinter/venv/bin/activate

# Iniciar servidor
cd /opt/labelprinter/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Acesse: http://SEU_IP:8000

### 7. Configurar como Servico (systemd)

```bash
# Criar arquivo de servico
sudo nano /etc/systemd/system/labelprinter.service
```

Conteudo:
```ini
[Unit]
Description=Sistema de Impressao de Etiquetas
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/labelprinter/backend
Environment="PATH=/opt/labelprinter/venv/bin"
ExecStart=/opt/labelprinter/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Ajustar permissoes
sudo chown -R www-data:www-data /opt/labelprinter

# Recarregar systemd
sudo systemctl daemon-reload

# Habilitar e iniciar servico
sudo systemctl enable labelprinter
sudo systemctl start labelprinter

# Verificar status
sudo systemctl status labelprinter
```

### 8. Configurar CUPS (Impressoras)

```bash
# Adicionar usuario ao grupo lpadmin
sudo usermod -a -G lpadmin www-data

# Acessar interface web do CUPS
# http://localhost:631

# Listar impressoras disponiveis
lpstat -p -d
```

### 9. Configurar Firewall (se necessario)

```bash
# UFW
sudo ufw allow 8000/tcp

# iptables
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
```

### 10. (Opcional) Configurar Nginx como Proxy Reverso

```bash
sudo apt install nginx -y
sudo nano /etc/nginx/sites-available/labelprinter
```

```nginx
server {
    listen 80;
    server_name etiquetas.suaempresa.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/labelprinter /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Configuracao do Sistema (Interface Web)

### 1. Acessar o Sistema
- Abra o navegador: http://SEU_IP:8000
- Acesse a aba "Configuracoes"

### 2. Configurar API Benu ERP
1. Acesse a aba "Configuracoes"
2. Na secao "Integracao Benu ERP"
3. Cole seu token de autenticacao (Bearer)
4. Clique em "Salvar Token"
5. Clique em "Testar Conexao" para verificar

### 3. Configurar Parametros de Etiqueta
1. Resolucao DPI (minimo 300)
2. Tamanho de fonte minimo (10 pontos)
3. Habilitar/desabilitar CEPNet
4. Habilitar/desabilitar Data Matrix

### 4. Configurar Data Matrix (Correios)
1. Selecione o IDV (tipo de servico)
2. Informe o CNAE da empresa

### 5. Configurar Impressoras
1. Acesse a aba "Impressoras"
2. Clique em "Detectar do Sistema"
3. Adicione as impressoras desejadas
4. Na aba "Configuracoes", defina a impressora padrao para cada tipo de etiqueta

### 6. Configurar Remetente
1. Na aba "Configuracoes", secao "Dados do Remetente"
2. Preencha todos os campos
3. Clique em "Salvar Remetente"

---

## Uso do Sistema

### Impressao de Etiquetas
1. Selecione o cliente
2. Escolha o endereco
3. Selecione o tipo de etiqueta
4. Opcionalmente, escolha uma impressora especifica
5. Defina a quantidade
6. Marque/desmarque opcoes (codigo de barras, remetente)
7. Clique em "Visualizar" para preview ou "Imprimir"

### Cadastro de Clientes
1. Acesse a aba "Clientes"
2. Clique em "Novo Cliente"
3. Preencha os dados
4. Adicione enderecos (o CEP sera buscado automaticamente)
5. Salve

---

## API Endpoints

### CEP (BrasilAPI)
- `GET /api/cep/{cep}` - Consulta CEP (com cache)
- `GET /api/cep/{cep}/v2` - Consulta CEP com geolocalizacao
- `GET /api/cep/cache/stats` - Estatisticas do cache
- `DELETE /api/cep/cache` - Limpar cache

### Configuracoes
- `GET /api/settings` - Todas as configuracoes
- `PUT /api/settings/{section}` - Atualizar secao
- `POST /api/settings/benu/token` - Definir token Benu
- `GET /api/settings/benu/test` - Testar conexao Benu

### Clientes e Enderecos
- `GET /api/clientes` - Listar clientes
- `POST /api/clientes` - Criar cliente
- `GET /api/clientes/{id}/enderecos` - Listar enderecos

### Impressao
- `POST /api/preview` - Gerar preview PDF
- `POST /api/download` - Download PDF
- `POST /api/imprimir` - Enviar para impressora

---

## Estrutura do Projeto

```
LabelPrinter/
├── backend/
│   ├── services/
│   │   ├── cep_service.py      # Integracao BrasilAPI
│   │   ├── benu_service.py     # Integracao Benu ERP
│   │   ├── correios_codes.py   # CEPNet e Data Matrix
│   │   └── settings_service.py # Configuracoes do sistema
│   ├── main.py                 # API FastAPI
│   ├── models.py               # Modelos SQLAlchemy
│   ├── schemas.py              # Schemas Pydantic
│   ├── label_generator.py      # Geracao de etiquetas
│   └── printer_service.py      # Integracao CUPS
├── frontend/
│   ├── templates/index.html
│   └── static/{css,js}
├── docker-compose.yml
├── Dockerfile
└── run.sh
```

---

## Documentacao Tecnica

Os padroes implementados estao documentados em:
- `BENU_API_INTEGRACAO_COMPLETA.md` - API Benu ERP
- `BRASILAPI_CEP_INTEGRACAO_TECNICA.md` - BrasilAPI CEP
- `CORREIOS_ENDERECAMENTO_ESPEC_TECNICAS.md` - Padrao Correios

---

## Solucao de Problemas

### Impressora nao aparece
```bash
# Verificar CUPS
sudo systemctl status cups
lpstat -p -d
```

### Erro de permissao
```bash
sudo chown -R www-data:www-data /opt/labelprinter
```

### Logs do sistema
```bash
sudo journalctl -u labelprinter -f
```

---

## Licenca

MIT License
