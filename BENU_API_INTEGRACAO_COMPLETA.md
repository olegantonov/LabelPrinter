
# 📘 Benu ERP – Documentação Técnica de Integração de API
Versão da API: 1.0.1  
Padrão: REST  
Formato: JSON  
Autenticação: Bearer Token  

---

## 1. Visão Geral
Esta documentação descreve como integrar sistemas externos ao Benu ERP por meio de sua API REST.

Base URL:
https://www.benuerp.com.br

---

## 2. Autenticação
Todas as requisições devem conter o header:

Authorization: Bearer SEU_TOKEN

Tokens inválidos retornam HTTP 401.

---

## 3. Padrões Técnicos
- HTTPS obrigatório
- JSON UTF-8
- Timeout recomendado: 30s
- Retry para erros 5xx

---

## 4. Módulo Financeiro

### 4.1 Partidas Simples
POST /erpFinanceiroWar/financeiro/relatoriosContador/partidasSimples

Body:
{
  "dataInicio": "01/01/2025",
  "dataFim": "31/01/2025",
  "download": "S"
}

---

### 4.2 Relatório de Extratos
POST /erpFinanceiroWar/financeiro/apiFinanceiro/relatorioExtratos

Body:
{
  "dtInicio": "01/01/2025",
  "dtFim": "31/01/2025",
  "cdContaCorrente": 123,
  "cdCentroCustos": 456
}

---

## 5. Webhook Financeiro
POST /erpFinanceiroWar/financeiro/webhook/{nrBd}

Eventos:
- PAGAMENTO_CRIADO
- PAGAMENTO_CONFIRMADO
- COBRANCA_VENCIDA

---

## 6. Serviços Operacionais
POST /new/servicos/servicosOperacionais/retornoRelatorioOS
POST /new/servicos/servicosOperacionais/retornoRelatorioOrcamentos

---

## 7. CRM

### Consulta de Cards
GET /erpCrmWar/servicosCrm/consultaFunil/consultarCards/{cdFunil}/{offSet}/{maxResults}

### Webhooks CRM
- cadastrarCard
- moverCard
- criarTarefa
- enviarEmail

---

## 8. Códigos HTTP
200 Sucesso  
400 Erro de validação  
401 Não autorizado  
500 Erro interno  

---

## 9. Boas Práticas
- Logs de integração
- Validação de payload
- Fila para webhooks

---

Documento gerado automaticamente.
