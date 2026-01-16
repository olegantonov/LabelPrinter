"""
Servico de integracao com Benu ERP
Conforme especificacao: BENU_API_INTEGRACAO_COMPLETA.md
"""
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime


class BenuService:
    """
    Integracao com Benu ERP API
    - Autenticacao: Bearer Token
    - Padrao: REST / JSON
    - Timeout recomendado: 30s
    """

    BASE_URL = "https://www.benuerp.com.br"

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.timeout = 30.0

    def set_token(self, token: str):
        """Define o token de autenticacao"""
        self.token = token

    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers com autenticacao"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Faz requisicao para a API Benu"""
        if not self.token:
            return {"error": True, "message": "Token nao configurado"}

        url = f"{self.BASE_URL}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(
                        url,
                        headers=self._get_headers(),
                        params=params
                    )
                else:
                    response = await client.post(
                        url,
                        headers=self._get_headers(),
                        json=data
                    )

                if response.status_code == 401:
                    return {"error": True, "message": "Token invalido ou expirado", "code": 401}

                if response.status_code == 400:
                    return {"error": True, "message": "Erro de validacao", "code": 400, "details": response.text}

                if response.status_code >= 500:
                    return {"error": True, "message": "Erro interno do servidor Benu", "code": response.status_code}

                response.raise_for_status()

                # Tenta parsear JSON, se falhar retorna resposta vazia
                try:
                    data = response.json()
                except Exception:
                    data = []

                return {"error": False, "data": data}

        except httpx.TimeoutException:
            return {"error": True, "message": "Timeout na conexao com Benu ERP"}
        except Exception as e:
            return {"error": True, "message": str(e)}

    async def test_connection(self) -> Dict[str, Any]:
        """Testa conexao com a API Benu"""
        if not self.token:
            return {"success": False, "message": "Token nao configurado"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/erpCrmWar/servicosCrm/consultaFunil/consultarCards/1/0/1",
                    headers=self._get_headers()
                )

                if response.status_code == 401:
                    return {"success": False, "message": "Token invalido ou expirado"}

                # 200 = OK, 204 = No Content (ambos sao sucesso)
                if response.status_code in [200, 204]:
                    return {"success": True, "message": "Conexao OK"}

                if response.status_code >= 400:
                    return {"success": False, "message": f"Erro HTTP {response.status_code}"}

                return {"success": True, "message": "Conexao OK"}

        except httpx.TimeoutException:
            return {"success": False, "message": "Timeout na conexao"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ============== Busca de Clientes/OS ==============

    async def buscar_os(
        self,
        termo: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca Ordens de Servico com dados de cliente
        Endpoint: POST /new/servicos/servicosOperacionais/retornoRelatorioOS
        """
        filtros = {}
        if termo:
            filtros["termo"] = termo
        if data_inicio:
            filtros["dataInicio"] = data_inicio
        if data_fim:
            filtros["dataFim"] = data_fim
        if status:
            filtros["status"] = status

        return await self._request(
            "POST",
            "/new/servicos/servicosOperacionais/retornoRelatorioOS",
            data=filtros
        )

    async def buscar_orcamentos(
        self,
        termo: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca Orcamentos com dados de cliente
        Endpoint: POST /new/servicos/servicosOperacionais/retornoRelatorioOrcamentos
        """
        filtros = {}
        if termo:
            filtros["termo"] = termo
        if data_inicio:
            filtros["dataInicio"] = data_inicio
        if data_fim:
            filtros["dataFim"] = data_fim

        return await self._request(
            "POST",
            "/new/servicos/servicosOperacionais/retornoRelatorioOrcamentos",
            data=filtros
        )

    async def consultar_cards_crm(
        self,
        cd_funil: int = 1,
        offset: int = 0,
        max_results: int = 100,
        termo_busca: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Consulta cards do CRM (clientes/leads)
        Endpoint: GET /erpCrmWar/servicosCrm/consultaFunil/consultarCards/{cdFunil}/{offSet}/{maxResults}
        """
        result = await self._request(
            "GET",
            f"/erpCrmWar/servicosCrm/consultaFunil/consultarCards/{cd_funil}/{offset}/{max_results}"
        )

        # Filtra por termo se fornecido
        if not result.get("error") and termo_busca and result.get("data"):
            dados = result["data"]
            if isinstance(dados, list):
                termo_lower = termo_busca.lower()
                dados_filtrados = [
                    item for item in dados
                    if termo_lower in str(item).lower()
                ]
                result["data"] = dados_filtrados

        return result

    # ============== Modulo Financeiro ==============

    async def get_partidas_simples(
        self,
        data_inicio: str,
        data_fim: str,
        download: str = "S"
    ) -> Dict[str, Any]:
        """
        Consulta partidas simples
        Endpoint: POST /erpFinanceiroWar/financeiro/relatoriosContador/partidasSimples
        """
        return await self._request(
            "POST",
            "/erpFinanceiroWar/financeiro/relatoriosContador/partidasSimples",
            data={
                "dataInicio": data_inicio,
                "dataFim": data_fim,
                "download": download
            }
        )

    async def get_relatorio_extratos(
        self,
        data_inicio: str,
        data_fim: str,
        conta_corrente: Optional[int] = None,
        centro_custos: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Consulta relatorio de extratos
        Endpoint: POST /erpFinanceiroWar/financeiro/apiFinanceiro/relatorioExtratos
        """
        data = {
            "dtInicio": data_inicio,
            "dtFim": data_fim
        }
        if conta_corrente:
            data["cdContaCorrente"] = conta_corrente
        if centro_custos:
            data["cdCentroCustos"] = centro_custos

        return await self._request(
            "POST",
            "/erpFinanceiroWar/financeiro/apiFinanceiro/relatorioExtratos",
            data=data
        )


# Instancia global
benu_service = BenuService()
