#!/bin/bash

# Script para iniciar o Sistema de Impressao de Etiquetas

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Sistema de Impressao de Etiquetas${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verificar se Python 3 esta instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Erro: Python 3 nao esta instalado${NC}"
    exit 1
fi

# Diretorio do script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend"

# Criar ambiente virtual se nao existir
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Criando ambiente virtual...${NC}"
    python3 -m venv venv
fi

# Ativar ambiente virtual
echo -e "${YELLOW}Ativando ambiente virtual...${NC}"
source venv/bin/activate

# Instalar dependencias
echo -e "${YELLOW}Instalando dependencias...${NC}"
pip install -q -r requirements.txt

# Criar diretorios necessarios
mkdir -p uploads generated_labels

# Copiar .env.example se .env nao existir
if [ ! -f ".env" ]; then
    cp ../.env.example .env 2>/dev/null || true
fi

# Iniciar servidor
echo ""
echo -e "${GREEN}Iniciando servidor...${NC}"
echo -e "${GREEN}Acesse: http://localhost:8000${NC}"
echo ""
echo -e "${YELLOW}Pressione Ctrl+C para encerrar${NC}"
echo ""

python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
