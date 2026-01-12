# 📮 BrasilAPI — Integração Técnica para *captura de CEP* (v1)

> **Objetivo:** padronizar a captura/validação de CEP no seu sistema e preencher automaticamente endereço (UF, cidade, bairro, logradouro), usando **BrasilAPI** como fonte principal e com fallback/boas práticas de produção.

**Base URL:** `https://brasilapi.com.br` citeturn1view1  
**Recurso:** CEP v1 e CEP v2 (com geolocalização) citeturn3view0  

---

## 1) Atenção aos Termos de Uso (evite bloqueios)
A BrasilAPI pede explicitamente para **não fazer crawling/varredura automatizada de CEPs** (ex.: loop de `00000000` até `99999999`). citeturn1view1  
**Implicação prática:** se você precisa de alto volume, implemente **cache**, **rate limit**, e *nunca* rode “scan” de base inteira.

---

## 2) Endpoint recomendado

### 2.1 CEP v1 (endereço básico)
**GET** `/api/cep/v1/{cep}` citeturn3view0turn3view1

Exemplo:
```http
GET https://brasilapi.com.br/api/cep/v1/89010025
Accept: application/json
```

O v1 normalmente retorna:
- `cep`
- `state` (UF)
- `city`
- `neighborhood`
- `street`
- `service` (provedor usado na consulta) citeturn3view1

> Quando você quer **apenas preencher endereço** (sem coordenadas), o v1 é suficiente.

### 2.2 CEP v2 (com geolocalização)
**GET** `/api/cep/v2/{cep}` citeturn3view0

Exemplo:
```http
GET https://brasilapi.com.br/api/cep/v2/01310930
Accept: application/json
```

> Use o v2 quando você precisa de **latitude/longitude** (ex.: mapa, cálculo de distância, logística).

---

## 3) Validação e normalização de CEP (produção)

### 3.1 Normalização
Aceite entrada do usuário em qualquer formato e normalize para **8 dígitos**.

Regras:
- Remover tudo que não for número
- Exigir exatamente 8 dígitos
- Ex.: `"01310-930"` → `"01310930"`

### 3.2 Validação (regex)
- Sem máscara: `^\d{8}$`
- Com ou sem hífen: `^\d{5}-?\d{3}$`

### 3.3 UX (recomendado)
- Dispare a consulta quando o input atingir 8 dígitos (ou no blur)
- Mostre loading/feedback
- Se retornar 404, permita preenchimento manual

---

## 4) Modelo de preenchimento automático no seu formulário

**Campos que você normalmente preenche/atualiza ao consultar CEP:**
- `UF` ← `state`
- `Cidade` ← `city`
- `Bairro` ← `neighborhood`
- `Logradouro` ← `street`
- `CEP` (normalizado) ← `cep` citeturn3view1

**Boas práticas:**
- Preencha e **trave** (read-only) os campos retornados, mas ofereça “Editar” caso o usuário diga que está errado.
- Não preencha número/complemento (isso é do usuário).
- Salve internamente qual `service` respondeu, útil para auditoria/debug. citeturn3view1

---

## 5) Tratamento de erros (o que fazer em cada caso)

### 5.1 HTTP 200
- Preencher campos
- Cachear resposta

### 5.2 HTTP 404 (CEP não encontrado)
- Exibir “CEP não encontrado”
- Liberar campos para preenchimento manual
- (Opcional) sugerir revisar dígitos

### 5.3 HTTP 429 / 5xx (indisponibilidade / rate limit)
- Implementar **retry com backoff exponencial**
- Usar cache (mesmo “stale-while-revalidate”)
- (Opcional) fallback para ViaCEP em último caso

---

## 6) Cache e performance (altamente recomendado)
Para evitar abuso e acelerar seu app:

### 6.1 Cache no backend (ideal)
- TTL sugerido: 30 dias (CEP quase não muda)
- Chave: `cep:{cep8}`
- Armazenamento: Redis/Memcached/DB

### 6.2 Cache no frontend (bom, mas secundário)
- Session/localStorage com TTL curto (ex.: 1 dia)
- Não confie como fonte de verdade

### 6.3 “Stale-While-Revalidate” (melhor UX)
- Responde instantâneo do cache
- Revalida em background e atualiza se necessário

---

## 7) Exemplos prontos (copiar e colar)

### 7.1 JavaScript/TypeScript (fetch)
```ts
function normalizeCep(input: string): string | null {
  const digits = input.replace(/\D/g, "");
  return /^\d{8}$/.test(digits) ? digits : null;
}

async function fetchCepV1(cepInput: string) {
  const cep = normalizeCep(cepInput);
  if (!cep) throw new Error("CEP inválido");

  const url = `https://brasilapi.com.br/api/cep/v1/${cep}`;
  const res = await fetch(url, { headers: { "Accept": "application/json" } });

  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Erro BrasilAPI: ${res.status}`);

  return res.json() as Promise<{
    cep: string;
    state: string;
    city: string;
    neighborhood: string;
    street: string;
    service: string;
  }>;
}
```

### 7.2 Python (requests)
```py
import re
import requests

def normalize_cep(value: str) -> str | None:
    digits = re.sub(r"\D", "", value or "")
    return digits if re.fullmatch(r"\d{8}", digits) else None

def fetch_cep_v1(cep_input: str, timeout: int = 10):
    cep = normalize_cep(cep_input)
    if not cep:
        raise ValueError("CEP inválido")

    url = f"https://brasilapi.com.br/api/cep/v1/{cep}"
    r = requests.get(url, headers={"Accept": "application/json"}, timeout=timeout)

    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()
```

---

## 8) Arquitetura recomendada (produção)

### 8.1 Frontend → Backend → BrasilAPI (preferível)
**Por quê?**
- Você controla cache/rate limit
- Evita CORS/limitações do navegador (e expor lógica)
- Permite fallback e observabilidade

**Fluxo:**
1. Front chama `/api/cep?cep=01310930`
2. Seu backend normaliza/valida
3. Backend verifica cache
4. Se miss → chama BrasilAPI
5. Salva cache → retorna ao front

### 8.2 Observabilidade
Logue sempre:
- `cep`
- `status_code`
- latência
- `service` (quando houver) citeturn3view1

---

## 9) Checklist rápido (para você plugar hoje)
- [ ] Normalizar CEP (8 dígitos)
- [ ] Validar antes de chamar a API
- [ ] Implementar cache (TTL longo)
- [ ] Tratar 404 com fallback de UX (manual)
- [ ] Retry com backoff para 5xx/429
- [ ] Não fazer varredura/loop de CEPs (ToS) citeturn1view1

---

### Referências
- BrasilAPI (página inicial e aviso de uso responsável). citeturn1view1  
- Exemplos de chamada dos endpoints CEP v1/v2. citeturn3view0  
- Campos retornados pelo CEP v1 (cep/state/city/neighborhood/street/service). citeturn3view1  
