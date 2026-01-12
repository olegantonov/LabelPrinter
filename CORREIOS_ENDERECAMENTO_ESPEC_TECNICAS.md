# 📦 Correios — Especificações Técnicas de Endereçamento de Correspondências (Guia Técnico v1.4 – 03/05/2021)

> Baseado no documento **“Endereçamento de Correspondências — Guia Técnico” (Correios), versão 1.4_03/05/2021**.

---

## 1) Objetivo do padrão
O endereçamento é o conjunto de informações que **identificam e orientam o caminho** da correspondência da postagem até a entrega. O correto preenchimento impacta diretamente a **efetividade e o prazo** da entrega, especialmente em ambientes de **triagem automatizada**.

---

## 2) Conceitos e requisitos fundamentais

### 2.1 Objeto mecanizável
Correspondência com formato padrão que atende aos requisitos para processamento por **sistemas de triagem automatizada**, aumentando agilidade na separação e na entrega.

### 2.2 Bloco de endereçamento
Recomenda-se seguir o **leiaute padronizado** em áreas (Áreas 1 a 6) para objetos mecanizáveis e não mecanizáveis, garantindo posicionamento correto de: remetente, destinatário, franqueamento e códigos.

### 2.3 Importância do CEP
- O CEP deve ser **correto e compatível com o logradouro**, pois guia o encaminhamento automatizado.
- Se o CEP estiver incorreto, a máquina encaminha pelo CEP, podendo causar **atraso, devolução** ou entrega incorreta.

---

## 3) Padrão do endereço (conteúdo textual legível)

As correspondências devem conter **remetente e destinatário**, cada um com os itens abaixo (quando aplicável):

1. **Nome do destinatário/remetente**  
   - Pessoa física: nome e sobrenome  
   - Pessoa jurídica: nome fantasia  
2. **Tipo de logradouro** (ex.: Rua, Avenida, Quadra, etc.)
3. **Nome do logradouro** (nome oficial atribuído pelo município)
4. **Número** (usar **s/n** quando não houver numeração)
5. **Complemento** (ex.: loja, bloco, apartamento, etc.)
6. **Bairro**  
   - **Distrito Federal (DF):** usar o modelo do IBGE: Brasília como município único; em RAs sem bairro, informar a RA como bairro; se houver bairro, informar bairro e RA entre parênteses (ex.: *Veredas (Brazlândia)*).
7. **CEP**  
   - O CEP é composto por **8 dígitos**  
   - **Não escrever “CEP” antes dos números**; não sublinhar nem separar por ponto
8. **Nome da localidade** (cidade/município)
9. **UF** (sigla da unidade federativa)

### 3.1 Exemplo de formatação (padrão sugerido)
```
DESTINATÁRIO: João da Silva
Avenida Paulista, 123, Loja B
Paraíso
01311-000 São Paulo/SP
```

---

## 4) Leiaute padronizado da correspondência (Áreas 1 a 6)

O leiaute recomenda uma divisão do envelope/objeto em áreas, para facilitar leitura humana e triagem automática.

### Área 1 — Conteúdo do remetente
- Logomarca, promoções, mensagens do remetente etc.
- **Endereço do remetente preferencialmente no verso**.
- Se houver endereço do remetente na Área 1, usar **fonte menor e diferente** do destinatário.

### Área 2 — Serviços adicionais (siglas)
Área destinada às siglas de serviços adicionais, quando contratados:
- **AR** (Aviso de Recebimento)
- **MP** (Mão Própria)
- **DD** (Devolução de Documentos)
- **VD** (Valor Declarado)

### Área 3 — Franqueamento (selo/chancela)
- Reservada para selo ou chancela.
- No serviço “Carta”, inserir a **data de postagem abaixo da chancela**.
- Chancelas (modelo e arte final) são fornecidas pelos Correios para clientes com contrato.
- Símbolos e dimensões típicas:
  - **Círculo**: entrega urgente (diâmetro 35 mm)
  - **Retângulo**: não urgente (25 × 35 mm)
  - **Triângulo**: devolução opcional (25 × 25 × 25 mm)
- Quando houver chancela de devolução física/eletrônica: deve ficar na Área 3, ao lado/abaixo, mantendo **distância mínima de 10 mm** da chancela do serviço principal.

### Área 4 — Bloco do destinatário (principal)
- Endereço do destinatário no padrão do item 3.
- Onde se aplica o **Data Matrix** (quando necessário) e elementos para leitura automática.

### Área 5 — Rastreamento + comprovação de entrega
- Código de rastreamento (texto + código de barras linear UCC-128).
- Campos de recebedor:
  - **Recebedor**
  - **Assinatura**
  - **Documento**
  (preenchidos pelo recebedor no ato da entrega)

### Área 6 — Uso exclusivo dos Correios
Área reservada para tratamentos operacionais internos.

---

## 5) Códigos e padrões de automação

## 5.1 Data Matrix (2D) — Conteúdo e estrutura
O **Data Matrix** contém informações que permitem automatizar etapas de triagem/entrega. Deve ser aplicado em correspondências **mecanizáveis**.

### Campos do Data Matrix (itens e tamanhos)
**Parte fixa + parte variável** (quantidades máximas conforme o guia):

| Item | Campo | Tamanho | Tipo |
|---:|---|---:|---|
| 1 | CEP de destino | 8 | Numérico |
| 2 | Complemento do CEP de destino | 5 | Numérico |
| 3 | CEP de origem/devolução | 8 | Numérico |
| 4 | Complemento do CEP de origem/devolução | 5 | Numérico |
| 5 | Validador do CEP de destino | 1 | Numérico |
| 6 | IDV | 2 | Numérico |
| 7 | CIF | 34 | Numérico |
| 8 | Serviços adicionais | 10 | Alfanumérico |
| 9 | Código do serviço principal | 5 | Numérico |
| 10 | Campo reserva | 15 | Numérico |
| 11 | CNAE | 9 | Numérico |
| 12 | Código de rastreamento | 13 | Alfanumérico |
| 13 | Campo livre do cliente | até 54 | Alfanumérico |
| 14 | Indicador de fim de dados | 1 (= `|`) | Alfanumérico |

### Regras específicas importantes (Data Matrix)
**Complemento do CEP (itens 2 e 4):**
- Representa o **número do imóvel no logradouro**.
- Se não houver ponto de entrega (ex.: **SN – sem número**), preencher com **00000**.

**Validador do CEP de destino (item 5):**
- Somar os 8 dígitos do CEP.
- Subtrair a soma do **múltiplo de 10 imediatamente superior**.  
  Ex.: CEP 71010050 → soma = 14 → próximo múltiplo = 20 → validador = 6.

**IDV (item 6):** identifica o tipo de serviço (exemplos do guia):
- 01 FAC Simples
- 03 Carta Simples
- 04 E-Carta Simples
- 16 FAC Registrado
- 17 Carta Registrada
- 27 Carta via Internet
- 28 E-Carta Registrado
*(há outros códigos na tabela do guia)*

**Serviços adicionais (item 8):**
- Campo de 10 dígitos.
- Cada serviço adicional possui 3 dígitos.
- Informar códigos em **ordem crescente** e completar o restante com **zeros à direita**.

**Campo reserva (item 10):**
- Preencher com **15 zeros**.

**CNAE (item 11):**
- Preencher com a classificação CNAE da empresa (referência IBGE / ISIC Rev 3).

**Indicador de fim de dados (item 14):**
- O caractere `|` delimita o final dos dados lidos pelos sistemas dos Correios.
- Informações após `|` podem ser usadas pelo cliente (não consideradas pelos sistemas de triagem).

### Tamanhos mínimos (formatos padrão do Data Matrix)
Os Correios definem 3 formatos padrão (módulos) com dimensões mínimas:
- **26 × 26** → **9,1 × 9,1 mm**
- **32 × 32** → **11,2 × 11,2 mm**
- **36 × 36** → **12,6 × 12,6 mm**

---

## 5.2 CEPNet (código de barras do CEP)
O **CEPNet** é o código de barras para identificação do CEP durante o processamento automático:
- Representa os **8 dígitos** do CEP.
- Composto por **47 barras** (cada dígito é representado por 5 barras: 2 altas e 3 baixas),
  além de **2 barras delimitadoras** (início e fim).
- Inclui **dígito verificador** calculado como:
  - Soma dos 8 dígitos do CEP
  - Subtrai do múltiplo de 10 imediatamente superior

### Altura mínima recomendada para impressão do CEPNet
- Fonte com altura mínima de **9 pontos** (~ **3 mm**)
- Recomendação: **10 pontos** (~ **3,5 mm**)

> Para detalhes aprofundados (algoritmos/definições), o guia referencia o documento específico “CEPNet e Data Matrix (FAC)”.

---

## 5.3 Código de rastreamento (texto + UCC-128)
O código de rastreamento identifica correspondências e deve ser impresso:
- **Em texto**
- **Codificado** em **código de barras linear UCC-128**

### Dimensões mínimas do código de barras (UCC-128)
- Dimensão total mínima: **66 × 15 mm**
  - **15 mm** altura
  - **56 mm** largura
  - **5 mm** margem de proteção horizontal

### Formatação textual recomendada (legibilidade humana)
Separar por espaços no formato:
`JC 123 456 789 BR`

---

## 6) Impressão e qualidade

### Resolução mínima recomendada
- **300 dpi** no mínimo
- Configuração “**Melhor**” ou “**Normal**”
- Evitar “**Rascunho**” e modo de economia de toner

> Rótulos em baixa qualidade podem comprometer o prazo de entrega.

---

## 7) Modelos de rótulos (etiquetas) e dimensões

### 7.1 Endereçamento manuscrito
- Para pessoas físicas, recomenda-se que **o CEP seja a única informação na última linha**.
- Preferir letras de forma para legibilidade.
- Anverso: destinatário | Verso: remetente.

### 7.2 Endereçamento automatizado (etiquetas)
Quando o cliente imprime em etiquetas (com ou sem SIGEP WEB), são recomendados padrões por folha:

#### 6 rótulos por folha
- **84,7 × 101,6 mm**
- Compatível com: Pimaco (6184), Avery (15664/18664), Colacril (CCO84/CC284)

#### 4 rótulos por folha
- **138,11 × 106,36 mm**
- Compatível com: Pimaco (6088/6288), Avery (15188/25188), Colacril (4083/4084)

---

## 8) Envelopes e normalização ABNT
O guia referencia normas ABNT para envelopes:
- **NBR 12699/2000** (classificação)
- **NBR 12972/2001** e **NBR 13314/2001** (padronização)

---

## 9) Checklist técnico (para implementar em sistema/print)
- [ ] Normalizar CEP (8 dígitos), sem “CEP:” antes do número
- [ ] Garantir endereço do destinatário completo (nome, logradouro, número/s/n, complemento, bairro, cidade/UF)
- [ ] Posicionar blocos e códigos conforme Áreas 1–6
- [ ] Se mecanizável: aplicar Data Matrix conforme estrutura e regras
- [ ] Para rastreáveis: imprimir código de rastreamento + UCC-128 (66 × 15 mm mínimo)
- [ ] Imprimir em 300 dpi (mínimo), evitar rascunho
- [ ] Usar etiquetas compatíveis (4 ou 6 por folha) quando aplicável

---

## 10) Referência do documento
**Correios — Endereçamento de Correspondências: Guia Técnico**  
Versão **1.4_03/05/2021**.
