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
                return {"error": False, "data": response.json()}

        except httpx.TimeoutException:
            return {"error": True, "message": "Timeout na conexao com Benu ERP"}
        except Exception as e:
            return {"error": True, "message": str(e)}

    async def test_connection(self) -> Dict[str, Any]:
        """Testa conexao com a API Benu"""
        # Faz uma requisicao simples para testar o token
        # Usando endpoint de CRM como teste
        result = await self._request(
            "GET",
            "/erpCrmWar/servicosCrm/consultaFunil/consultarCards/1/0/1"
        )

        if result.get("error"):
            if result.get("code") == 401:
                return {"success": False, "message": "Token invalido"}
            return {"success": False, "message": result.get("message", "Erro desconhecido")}

        return {"success": True, "message": "Conexao OK"}

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

    # ============== Modulo CRM ==============

    async def consultar_cards(
        self,
        cd_funil: int,
        offset: int = 0,
        max_results: int = 50
    ) -> Dict[str, Any]:
        """
        Consulta cards do CRM
        Endpoint: GET /erpCrmWar/servicosCrm/consultaFunil/consultarCards/{cdFunil}/{offSet}/{maxResults}
        """
        return await self._request(
            "GET",
            f"/erpCrmWar/servicosCrm/consultaFunil/consultarCards/{cd_funil}/{offset}/{max_results}"
        )

    # ============== Servicos Operacionais ==============

    async def get_relatorio_os(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consulta relatorio de OS
        Endpoint: POST /new/servicos/servicosOperacionais/retornoRelatorioOS
        """
        return await self._request(
            "POST",
            "/new/servicos/servicosOperacionais/retornoRelatorioOS",
            data=filtros
        )

    async def get_relatorio_orcamentos(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consulta relatorio de orcamentos
        Endpoint: POST /new/servicos/servicosOperacionais/retornoRelatorioOrcamentos
        """
        return await self._request(
            "POST",
            "/new/servicos/servicosOperacionais/retornoRelatorioOrcamentos",
            data=filtros
        )


# Instancia global
benu_service = BenuService()
