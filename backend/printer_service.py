"""
Serviço de impressão - integração com sistema de impressão do Linux
"""
import subprocess
import os
from typing import List, Optional, Dict, Any
import tempfile
from config import settings


class PrinterService:
    """
    Serviço para gerenciar impressões no Linux
    Utiliza CUPS (Common UNIX Printing System)
    """

    @staticmethod
    def list_printers() -> List[Dict[str, Any]]:
        """
        Lista todas as impressoras disponíveis no sistema
        """
        printers = []

        try:
            # Listar impressoras usando lpstat
            result = subprocess.run(
                ['lpstat', '-p', '-d'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.startswith('printer '):
                        parts = line.split()
                        if len(parts) >= 2:
                            printer_name = parts[1]
                            is_enabled = 'enabled' in line.lower()
                            printers.append({
                                'name': printer_name,
                                'enabled': is_enabled,
                                'status': 'idle' if is_enabled else 'disabled'
                            })

            # Verificar impressora padrão
            if 'system default destination:' in result.stdout.lower():
                for line in result.stdout.split('\n'):
                    if 'system default destination:' in line.lower():
                        default_printer = line.split(':')[-1].strip()
                        for p in printers:
                            if p['name'] == default_printer:
                                p['is_default'] = True
                                break

        except FileNotFoundError:
            # CUPS não instalado
            pass
        except Exception as e:
            print(f"Erro ao listar impressoras: {e}")

        return printers

    @staticmethod
    def get_printer_info(printer_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações detalhadas de uma impressora
        """
        try:
            result = subprocess.run(
                ['lpstat', '-p', printer_name, '-l'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return {
                    'name': printer_name,
                    'info': result.stdout.strip()
                }
        except Exception as e:
            print(f"Erro ao obter info da impressora: {e}")

        return None

    @staticmethod
    def print_pdf(
        pdf_content: bytes,
        printer_name: str,
        copies: int = 1,
        options: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Envia um PDF para impressão
        """
        try:
            # Criar arquivo temporário com o PDF
            with tempfile.NamedTemporaryFile(
                suffix='.pdf',
                delete=False,
                dir=settings.LABELS_DIR
            ) as tmp_file:
                tmp_file.write(pdf_content)
                tmp_path = tmp_file.name

            # Montar comando lp
            cmd = ['lp', '-d', printer_name, '-n', str(copies)]

            # Adicionar opções extras
            if options:
                for key, value in options.items():
                    cmd.extend(['-o', f'{key}={value}'])

            cmd.append(tmp_path)

            # Executar impressão
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            # Remover arquivo temporário
            os.unlink(tmp_path)

            if result.returncode == 0:
                return True
            else:
                print(f"Erro na impressão: {result.stderr}")
                return False

        except Exception as e:
            print(f"Erro ao imprimir: {e}")
            return False

    @staticmethod
    def print_label(
        pdf_content: bytes,
        printer_name: str,
        label_type: str,
        copies: int = 1
    ) -> bool:
        """
        Imprime uma etiqueta com configurações específicas para o tipo
        """
        options = {}

        # Configurações específicas por tipo de etiqueta
        if label_type.startswith("thermal_"):
            # Etiquetas térmicas geralmente não precisam de opções especiais
            # mas podem ser configuradas de acordo com a impressora
            options['fit-to-page'] = 'true'

        elif label_type == "pimaco_a4":
            # Configurações para folha A4
            options['media'] = 'A4'
            options['fit-to-page'] = 'false'

        elif label_type == "envelope_dl":
            options['media'] = 'DL'
            options['orientation-requested'] = '4'  # Landscape

        elif label_type == "envelope_c5":
            options['media'] = 'C5'
            options['orientation-requested'] = '4'  # Landscape

        return PrinterService.print_pdf(pdf_content, printer_name, copies, options)

    @staticmethod
    def test_printer(printer_name: str) -> bool:
        """
        Testa se a impressora está respondendo
        """
        try:
            result = subprocess.run(
                ['lpstat', '-p', printer_name],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def get_print_queue(printer_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtém a fila de impressão
        """
        queue = []

        try:
            cmd = ['lpq']
            if printer_name:
                cmd.extend(['-P', printer_name])

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[2:]:  # Pular cabeçalho
                    if line.strip():
                        queue.append({'raw': line})

        except Exception as e:
            print(f"Erro ao obter fila: {e}")

        return queue

    @staticmethod
    def cancel_job(job_id: str, printer_name: Optional[str] = None) -> bool:
        """
        Cancela um trabalho de impressão
        """
        try:
            cmd = ['cancel', job_id]
            if printer_name:
                cmd.extend(['-P', printer_name])

            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0

        except Exception:
            return False


# Instância global
printer_service = PrinterService()
