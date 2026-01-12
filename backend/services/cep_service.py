"""
Servico de consulta de CEP via BrasilAPI
Conforme especificacao: BRASILAPI_CEP_INTEGRACAO_TECNICA.md
"""
import re
import httpx
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

# Diretorio de cache
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / "cep_cache.json"
CACHE_TTL_DAYS = 30  # TTL recomendado: 30 dias


class CepService:
    """
    Servico de consulta de CEP usando BrasilAPI
    - Normalizacao de CEP (8 digitos)
    - Cache local com TTL de 30 dias
    - Fallback para preenchimento manual em caso de erro
    """

    BASE_URL = "https://brasilapi.com.br"

    def __init__(self):
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Carrega cache do disco"""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        """Salva cache no disco"""
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar cache: {e}")

    def _is_cache_valid(self, cached_data: Dict) -> bool:
        """Verifica se o cache ainda e valido (TTL 30 dias)"""
        if 'cached_at' not in cached_data:
            return False

        cached_at = datetime.fromisoformat(cached_data['cached_at'])
        return datetime.now() - cached_at < timedelta(days=CACHE_TTL_DAYS)

    @staticmethod
    def normalize_cep(cep_input: str) -> Optional[str]:
        """
        Normaliza CEP para 8 digitos
        Aceita formatos: 01310-930, 01310930, 01.310-930
        Retorna None se invalido
        """
        if not cep_input:
            return None

        # Remove tudo que nao for digito
        digits = re.sub(r'\D', '', cep_input)

        # Valida: exatamente 8 digitos
        if re.fullmatch(r'\d{8}', digits):
            return digits

        return None

    @staticmethod
    def format_cep(cep: str) -> str:
        """Formata CEP com hifen: 01310930 -> 01310-930"""
        cep_clean = re.sub(r'\D', '', cep)
        if len(cep_clean) == 8:
            return f"{cep_clean[:5]}-{cep_clean[5:]}"
        return cep

    @staticmethod
    def validate_cep(cep_input: str) -> bool:
        """Valida formato do CEP"""
        return CepService.normalize_cep(cep_input) is not None

    async def fetch_cep_v1(self, cep_input: str) -> Optional[Dict[str, Any]]:
        """
        Consulta CEP na BrasilAPI v1
        Retorna: cep, state, city, neighborhood, street, service
        """
        cep = self.normalize_cep(cep_input)
        if not cep:
            return None

        # Verificar cache primeiro
        cache_key = f"cep:{cep}"
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            return self.cache[cache_key]['data']

        # Consultar API
        url = f"{self.BASE_URL}/api/cep/v1/{cep}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url,
                    headers={"Accept": "application/json"}
                )

                if response.status_code == 404:
                    # CEP nao encontrado
                    return None

                if response.status_code == 429:
                    # Rate limit - tentar cache mesmo expirado
                    if cache_key in self.cache:
                        return self.cache[cache_key].get('data')
                    return None

                response.raise_for_status()
                data = response.json()

                # Salvar no cache
                self.cache[cache_key] = {
                    'data': data,
                    'cached_at': datetime.now().isoformat()
                }
                self._save_cache()

                return data

        except httpx.TimeoutException:
            # Timeout - retornar cache se existir
            if cache_key in self.cache:
                return self.cache[cache_key].get('data')
            return None
        except Exception as e:
            print(f"Erro ao consultar CEP: {e}")
            # Tentar cache em caso de erro
            if cache_key in self.cache:
                return self.cache[cache_key].get('data')
            return None

    async def fetch_cep_v2(self, cep_input: str) -> Optional[Dict[str, Any]]:
        """
        Consulta CEP na BrasilAPI v2 (com geolocalizacao)
        Retorna dados adicionais: location (latitude, longitude)
        """
        cep = self.normalize_cep(cep_input)
        if not cep:
            return None

        cache_key = f"cep_v2:{cep}"
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            return self.cache[cache_key]['data']

        url = f"{self.BASE_URL}/api/cep/v2/{cep}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url,
                    headers={"Accept": "application/json"}
                )

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                data = response.json()

                self.cache[cache_key] = {
                    'data': data,
                    'cached_at': datetime.now().isoformat()
                }
                self._save_cache()

                return data

        except Exception as e:
            print(f"Erro ao consultar CEP v2: {e}")
            if cache_key in self.cache:
                return self.cache[cache_key].get('data')
            return None

    def map_to_address(self, cep_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Mapeia resposta da BrasilAPI para formato de endereco do sistema
        """
        return {
            'cep': self.format_cep(cep_data.get('cep', '')),
            'logradouro': cep_data.get('street', ''),
            'bairro': cep_data.get('neighborhood', ''),
            'cidade': cep_data.get('city', ''),
            'estado': cep_data.get('state', ''),
            'service': cep_data.get('service', '')  # Para auditoria
        }

    def clear_cache(self):
        """Limpa todo o cache"""
        self.cache = {}
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatisticas do cache"""
        total = len(self.cache)
        valid = sum(1 for v in self.cache.values() if self._is_cache_valid(v))
        return {
            'total_entries': total,
            'valid_entries': valid,
            'expired_entries': total - valid
        }


# Instancia global
cep_service = CepService()
