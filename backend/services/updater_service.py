"""
Servico de auto-atualizacao do sistema
Verifica periodicamente se ha atualizacoes no repositorio Git
"""
import subprocess
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UpdaterService:
    """
    Servico que verifica e aplica atualizacoes automaticamente
    """

    def __init__(self, repo_path: Optional[str] = None):
        # Detecta o caminho do repositorio
        self.repo_path = repo_path or self._detect_repo_path()
        self.branch = "claude/label-printing-system-mVJIp"
        self.check_interval = 3600  # 1 hora em segundos
        self.last_check: Optional[datetime] = None
        self.last_update: Optional[datetime] = None
        self._running = False

    def _detect_repo_path(self) -> str:
        """Detecta o caminho raiz do repositorio"""
        # Tenta encontrar a raiz do git
        current = os.path.dirname(os.path.abspath(__file__))

        # Sobe na hierarquia procurando .git
        path = current
        for _ in range(5):  # Maximo 5 niveis
            if os.path.exists(os.path.join(path, ".git")):
                return path
            parent = os.path.dirname(path)
            if parent == path:  # Chegou na raiz
                break
            path = parent

        # Fallback: sobe dois niveis (services -> backend -> LabelPrinter)
        return os.path.dirname(os.path.dirname(current))

    def _run_git_command(self, *args) -> Dict[str, Any]:
        """Executa comando git e retorna resultado"""
        try:
            logger.info(f"Executando git {' '.join(args)} em {self.repo_path}")
            result = subprocess.run(
                ["git"] + list(args),
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            logger.info(f"Git retornou: {result.returncode}, stdout: {result.stdout[:100] if result.stdout else 'vazio'}")
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip()
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout executando git"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_current_version(self) -> Dict[str, Any]:
        """Retorna versao atual (commit hash)"""
        result = self._run_git_command("rev-parse", "HEAD")
        if result["success"]:
            # Pega tambem o branch atual
            branch_result = self._run_git_command("rev-parse", "--abbrev-ref", "HEAD")
            return {
                "commit": result["stdout"][:8],
                "full_commit": result["stdout"],
                "branch": branch_result.get("stdout", "unknown") if branch_result.get("success") else "unknown",
                "repo_path": self.repo_path
            }
        return {"commit": "unknown", "error": result.get("error", result.get("stderr"))}

    def get_current_branch(self) -> str:
        """Retorna o branch atual"""
        result = self._run_git_command("rev-parse", "--abbrev-ref", "HEAD")
        return result.get("stdout", "unknown") if result.get("success") else "unknown"

    def check_for_updates(self) -> Dict[str, Any]:
        """Verifica se ha atualizacoes disponiveis"""
        self.last_check = datetime.now()

        # Verifica branch atual
        current_branch = self.get_current_branch()
        target_branch = self.branch

        # Se esta em outro branch, usa o branch atual
        if current_branch != target_branch and current_branch != "HEAD":
            logger.info(f"Branch atual ({current_branch}) diferente do esperado ({target_branch}). Usando branch atual.")
            target_branch = current_branch

        # Fetch das atualizacoes
        fetch_result = self._run_git_command("fetch", "origin", target_branch)
        if not fetch_result["success"]:
            # Tenta fetch geral
            fetch_result = self._run_git_command("fetch", "--all")
            if not fetch_result["success"]:
                return {
                    "available": False,
                    "error": f"Erro ao buscar atualizacoes: {fetch_result.get('stderr', fetch_result.get('error'))}",
                    "current_branch": current_branch,
                    "repo_path": self.repo_path
                }

        # Compara commits
        local = self._run_git_command("rev-parse", "HEAD")
        remote = self._run_git_command("rev-parse", f"origin/{target_branch}")

        if not local["success"]:
            return {"available": False, "error": "Erro ao obter versao local", "current_branch": current_branch}

        if not remote["success"]:
            return {
                "available": False,
                "error": f"Erro ao obter versao remota: {remote.get('stderr')}",
                "current_branch": current_branch
            }

        local_commit = local["stdout"]
        remote_commit = remote["stdout"]

        if local_commit != remote_commit:
            # Conta commits atras
            count_result = self._run_git_command(
                "rev-list", "--count", f"HEAD..origin/{target_branch}"
            )
            commits_behind = int(count_result["stdout"]) if count_result["success"] and count_result["stdout"].isdigit() else 0

            return {
                "available": True,
                "current_commit": local_commit[:8],
                "latest_commit": remote_commit[:8],
                "commits_behind": commits_behind,
                "current_branch": current_branch
            }

        return {
            "available": False,
            "current_commit": local_commit[:8],
            "message": "Sistema atualizado",
            "current_branch": current_branch
        }

    def apply_update(self) -> Dict[str, Any]:
        """Aplica atualizacoes do repositorio"""
        logger.info("Iniciando atualizacao do sistema...")

        current_branch = self.get_current_branch()
        target_branch = current_branch if current_branch != "HEAD" else self.branch

        # Pull das mudancas
        pull_result = self._run_git_command("pull", "origin", target_branch)

        if not pull_result["success"]:
            logger.error(f"Erro no pull: {pull_result.get('stderr')}")
            return {
                "success": False,
                "error": f"Erro ao atualizar: {pull_result.get('stderr', pull_result.get('error'))}"
            }

        self.last_update = datetime.now()
        logger.info("Atualizacao concluida com sucesso")

        return {
            "success": True,
            "message": "Atualizacao aplicada com sucesso",
            "output": pull_result["stdout"],
            "restart_required": True
        }

    def get_status(self) -> Dict[str, Any]:
        """Retorna status do sistema de atualizacao"""
        version = self.get_current_version()
        current_branch = self.get_current_branch()

        # Verifica se o diretório .git existe
        git_exists = os.path.exists(os.path.join(self.repo_path, ".git"))

        return {
            "current_version": version.get("commit", "unknown"),
            "repo_path": self.repo_path,
            "branch": current_branch,
            "expected_branch": self.branch,
            "git_initialized": git_exists,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "auto_update_enabled": self._running,
            "check_interval_seconds": self.check_interval
        }

    async def auto_update_loop(self):
        """Loop de verificacao automatica de atualizacoes"""
        self._running = True
        logger.info(f"Iniciando verificacao automatica a cada {self.check_interval}s")

        while self._running:
            try:
                await asyncio.sleep(self.check_interval)

                logger.info("Verificando atualizacoes...")
                check = self.check_for_updates()

                if check.get("available"):
                    logger.info(f"Atualizacao disponivel: {check.get('commits_behind')} commits atras")
                    update_result = self.apply_update()

                    if update_result.get("success") and update_result.get("restart_required"):
                        logger.info("Reinicio necessario para aplicar atualizacoes")
                else:
                    logger.info("Sistema ja esta atualizado")

            except asyncio.CancelledError:
                logger.info("Loop de atualizacao cancelado")
                break
            except Exception as e:
                logger.error(f"Erro no loop de atualizacao: {e}")

        self._running = False

    def stop_auto_update(self):
        """Para o loop de atualizacao automatica"""
        self._running = False


# Instancia global
updater_service = UpdaterService()
