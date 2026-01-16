"""
Servico de integracao com Benu ERP
Conforme documentacao oficial da API Benu
"""
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta


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

    # ============== Busca de OS ==============

    async def buscar_os(
        self,
        nome_cliente: Optional[str] = None,
        cd_cliente: Optional[int] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca Ordens de Servico
        Endpoint: POST /new/servicos/servicosOperacionais/retornoRelatorioOS

        Parametros obrigatorios: dataInicio e dataFim OU cdServico
        """
        # Se nao informar datas, usa ultimos 30 dias
        if not data_inicio:
            data_inicio = (datetime.now() - timedelta(days=30)).strftime("%d/%m/%Y")
        if not data_fim:
            data_fim = datetime.now().strftime("%d/%m/%Y")

        filtros = {
            "dataInicio": data_inicio,
            "dataFim": data_fim
        }

        if nome_cliente:
            filtros["nmCliente"] = nome_cliente
        if cd_cliente:
            filtros["cdCliente"] = cd_cliente

        return await self._request(
            "POST",
            "/new/servicos/servicosOperacionais/retornoRelatorioOS",
            data=filtros
        )

    # ============== Busca de Orcamentos ==============

    async def buscar_orcamentos(
        self,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        cd_vendedor: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Busca Orcamentos
        Endpoint: POST /new/servicos/servicosOperacionais/retornoRelatorioOrcamentos

        Parametros obrigatorios: inicio e fim
        """
        # Se nao informar datas, usa ultimos 30 dias
        if not data_inicio:
            data_inicio = (datetime.now() - timedelta(days=30)).strftime("%d/%m/%Y")
        if not data_fim:
            data_fim = datetime.now().strftime("%d/%m/%Y")

        filtros = {
            "inicio": data_inicio,
            "fim": data_fim
        }

        if cd_vendedor:
            filtros["cdVendedor"] = cd_vendedor

        return await self._request(
            "POST",
            "/new/servicos/servicosOperacionais/retornoRelatorioOrcamentos",
            data=filtros
        )

    # ============== Busca de Cards CRM ==============

    async def consultar_cards_crm(
        self,
        cd_funil: int = 1,
        offset: int = 0,
        max_results: int = 100
    ) -> Dict[str, Any]:
        """
        Consulta cards do CRM (clientes/leads)
        Endpoint: GET /erpCrmWar/servicosCrm/consultaFunil/consultarCards/{cdFunil}/{offSet}/{maxResults}
        """
        return await self._request(
            "GET",
            f"/erpCrmWar/servicosCrm/consultaFunil/consultarCards/{cd_funil}/{offset}/{max_results}"
        )

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
