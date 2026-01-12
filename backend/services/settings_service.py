"""
Servico de configuracoes do sistema
Armazena API keys, parametros tecnicos e preferencias
"""
import json
import os
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

# Arquivo de configuracoes
CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_DIR.mkdir(exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "system_settings.json"


class SystemSettings:
    """
    Gerenciador de configuracoes do sistema
    Armazena de forma segura:
    - API Keys (Benu ERP)
    - Parametros de integracao
    - Configuracoes de etiquetas
    - Dados do remetente
    """

    DEFAULT_SETTINGS = {
        # API Keys e Integracoes
        "benu_api": {
            "enabled": False,
            "token": "",
            "base_url": "https://www.benuerp.com.br",
            "timeout": 30
        },

        "brasilapi": {
            "enabled": True,
            "cache_ttl_days": 30,
            "use_v2": False  # v2 inclui geolocalizacao
        },

        # Configuracoes de Etiquetas (padrao Correios)
        "etiquetas": {
            "resolucao_dpi": 300,  # Minimo recomendado pelos Correios
            "incluir_datamatrix": True,
            "incluir_cepnet": True,
            "formato_cep": "99999-999",  # Sem "CEP:" antes
            "fonte_padrao": "Helvetica",
            "tamanho_fonte_min": 10  # Pontos
        },

        # Dados do Remetente
        "remetente": {
            "nome": "",
            "logradouro": "",
            "numero": "",
            "complemento": "",
            "bairro": "",
            "cidade": "",
            "estado": "",
            "cep": "",
            "cnpj": "",
            "telefone": ""
        },

        # Configuracoes de Impressao
        "impressao": {
            "cups_enabled": True,
            "usar_impressora_padrao": True,
            "qualidade": "normal"  # rascunho, normal, alta
        },

        # Data Matrix (conforme especificacao Correios)
        "datamatrix": {
            "idv_padrao": "03",  # 03 = Carta Simples
            "cnae": "",
            "servicos_adicionais": ""
        },

        # Metadados
        "metadata": {
            "version": "1.0.0",
            "last_updated": None
        }
    }

    def __init__(self):
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """Carrega configuracoes do disco"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    # Merge com defaults para garantir novos campos
                    return self._merge_defaults(saved)
            except Exception as e:
                print(f"Erro ao carregar configuracoes: {e}")
                return self.DEFAULT_SETTINGS.copy()
        return self.DEFAULT_SETTINGS.copy()

    def _merge_defaults(self, saved: Dict) -> Dict:
        """Merge configuracoes salvas com defaults"""
        result = self.DEFAULT_SETTINGS.copy()

        def deep_merge(base: Dict, override: Dict) -> Dict:
            for key, value in override.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = deep_merge(base[key], value)
                else:
                    base[key] = value
            return base

        return deep_merge(result, saved)

    def _save_settings(self):
        """Salva configuracoes no disco"""
        self.settings["metadata"]["last_updated"] = datetime.now().isoformat()
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar configuracoes: {e}")

    # ============== Getters ==============

    def get_all(self) -> Dict[str, Any]:
        """Retorna todas as configuracoes (ocultando tokens)"""
        result = self.settings.copy()
        # Ocultar token para exibicao
        if result.get("benu_api", {}).get("token"):
            token = result["benu_api"]["token"]
            result["benu_api"]["token_masked"] = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else "***"
            result["benu_api"]["token_set"] = True
        else:
            result["benu_api"]["token_masked"] = ""
            result["benu_api"]["token_set"] = False
        return result

    def get(self, section: str, key: Optional[str] = None) -> Any:
        """Obtem uma configuracao especifica"""
        if section not in self.settings:
            return None

        if key is None:
            return self.settings[section]

        return self.settings[section].get(key)

    def get_benu_token(self) -> Optional[str]:
        """Retorna token do Benu ERP (nao mascarado)"""
        return self.settings.get("benu_api", {}).get("token")

    def get_remetente(self) -> Dict[str, str]:
        """Retorna dados do remetente"""
        return self.settings.get("remetente", {})

    def get_etiqueta_config(self) -> Dict[str, Any]:
        """Retorna configuracoes de etiqueta"""
        return self.settings.get("etiquetas", {})

    def get_datamatrix_config(self) -> Dict[str, Any]:
        """Retorna configuracoes do Data Matrix"""
        return self.settings.get("datamatrix", {})

    # ============== Setters ==============

    def update(self, section: str, data: Dict[str, Any]) -> bool:
        """Atualiza uma secao de configuracoes"""
        if section not in self.settings:
            return False

        self.settings[section].update(data)
        self._save_settings()
        return True

    def set_benu_token(self, token: str) -> bool:
        """Define o token do Benu ERP"""
        self.settings["benu_api"]["token"] = token
        self._save_settings()
        return True

    def set_remetente(self, data: Dict[str, str]) -> bool:
        """Define dados do remetente"""
        self.settings["remetente"].update(data)
        self._save_settings()
        return True

    def set_etiqueta_config(self, data: Dict[str, Any]) -> bool:
        """Define configuracoes de etiqueta"""
        self.settings["etiquetas"].update(data)
        self._save_settings()
        return True

    def set_datamatrix_config(self, data: Dict[str, Any]) -> bool:
        """Define configuracoes do Data Matrix"""
        self.settings["datamatrix"].update(data)
        self._save_settings()
        return True

    # ============== Validacoes ==============

    def validate_benu_config(self) -> Dict[str, Any]:
        """Valida configuracoes do Benu ERP"""
        benu = self.settings.get("benu_api", {})
        errors = []

        if benu.get("enabled") and not benu.get("token"):
            errors.append("Token do Benu ERP e obrigatorio quando habilitado")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def validate_remetente(self) -> Dict[str, Any]:
        """Valida dados do remetente"""
        rem = self.settings.get("remetente", {})
        errors = []

        required = ["nome", "logradouro", "numero", "bairro", "cidade", "estado", "cep"]
        for field in required:
            if not rem.get(field):
                errors.append(f"Campo '{field}' do remetente e obrigatorio")

        # Validar CEP
        if rem.get("cep"):
            import re
            cep_clean = re.sub(r'\D', '', rem["cep"])
            if len(cep_clean) != 8:
                errors.append("CEP do remetente deve ter 8 digitos")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    # ============== Reset ==============

    def reset_section(self, section: str) -> bool:
        """Reseta uma secao para valores padrao"""
        if section in self.DEFAULT_SETTINGS:
            self.settings[section] = self.DEFAULT_SETTINGS[section].copy()
            self._save_settings()
            return True
        return False

    def reset_all(self) -> bool:
        """Reseta todas as configuracoes para padrao"""
        self.settings = self.DEFAULT_SETTINGS.copy()
        self._save_settings()
        return True


# Instancia global
system_settings = SystemSettings()
