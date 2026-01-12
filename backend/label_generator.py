"""
Gerador de etiquetas com suporte a código de barras dos Correios
"""
import io
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import barcode
from barcode.writer import ImageWriter
from PIL import Image
from config import LABEL_SIZES, settings


class CorreiosBarcode:
    """
    Gera código de barras no padrão dos Correios
    O código de barras dos Correios utiliza o CEP com dígito verificador
    """

    @staticmethod
    def calculate_check_digit(cep: str) -> int:
        """
        Calcula o dígito verificador do CEP no padrão Correios
        Utiliza módulo 10 com multiplicadores 1 e 2
        """
        cep_digits = [int(d) for d in cep.replace("-", "").replace(".", "")]

        # Multiplicadores alternados: 1, 2, 1, 2, 1, 2, 1, 2
        multipliers = [1, 2, 1, 2, 1, 2, 1, 2]

        total = 0
        for digit, mult in zip(cep_digits, multipliers):
            result = digit * mult
            # Se resultado > 9, soma os dígitos
            if result > 9:
                result = (result // 10) + (result % 10)
            total += result

        # Dígito verificador
        remainder = total % 10
        if remainder == 0:
            return 0
        return 10 - remainder

    @staticmethod
    def format_cep_barcode(cep: str) -> str:
        """
        Formata o CEP para código de barras incluindo dígito verificador
        """
        cep_clean = cep.replace("-", "").replace(".", "")
        check_digit = CorreiosBarcode.calculate_check_digit(cep_clean)
        return f"{cep_clean}{check_digit}"

    @staticmethod
    def generate_barcode_image(cep: str, width: int = 200, height: int = 50) -> Image.Image:
        """
        Gera imagem do código de barras para o CEP
        Utiliza Code128 que é compatível com Correios
        """
        barcode_data = CorreiosBarcode.format_cep_barcode(cep)

        # Usar Code128 (padrão aceito pelos Correios)
        code128 = barcode.get_barcode_class('code128')

        # Configurar writer com opções
        writer = ImageWriter()
        writer.set_options({
            'module_width': 0.3,
            'module_height': 8,
            'quiet_zone': 2,
            'font_size': 8,
            'text_distance': 3,
            'write_text': True
        })

        # Gerar código de barras
        barcode_obj = code128(barcode_data, writer=writer)

        # Salvar em buffer
        buffer = io.BytesIO()
        barcode_obj.write(buffer)
        buffer.seek(0)

        # Abrir como imagem PIL
        img = Image.open(buffer)

        return img


class LabelGenerator:
    """
    Gerador de etiquetas em diversos formatos
    """

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.remetente: Optional[Dict[str, str]] = None

    def set_remetente(self, remetente: Dict[str, str]):
        """Define os dados do remetente"""
        self.remetente = remetente

    def _format_address(self, endereco: Dict[str, Any], nome: str) -> List[str]:
        """Formata o endereço para exibição na etiqueta"""
        lines = []

        # Destinatário
        destinatario = endereco.get('destinatario') or nome
        lines.append(destinatario.upper())

        # Logradouro com número e complemento
        logradouro = f"{endereco['logradouro']}, {endereco['numero']}"
        if endereco.get('complemento'):
            logradouro += f" - {endereco['complemento']}"
        lines.append(logradouro)

        # Bairro
        lines.append(endereco['bairro'])

        # CEP - Cidade/UF
        cep = endereco['cep']
        if '-' not in cep:
            cep = f"{cep[:5]}-{cep[5:]}"
        lines.append(f"{cep} - {endereco['cidade']}/{endereco['estado'].upper()}")

        return lines

    def _format_remetente(self) -> List[str]:
        """Formata os dados do remetente"""
        if not self.remetente:
            return []

        lines = []
        lines.append(f"Rem: {self.remetente['nome']}")

        logradouro = f"{self.remetente['logradouro']}, {self.remetente['numero']}"
        if self.remetente.get('complemento'):
            logradouro += f" - {self.remetente['complemento']}"
        lines.append(logradouro)

        cep = self.remetente['cep']
        if '-' not in cep:
            cep = f"{cep[:5]}-{cep[5:]}"
        lines.append(f"{cep} - {self.remetente['cidade']}/{self.remetente['estado'].upper()}")

        return lines

    def generate_thermal_label(
        self,
        cliente_nome: str,
        endereco: Dict[str, Any],
        size: str = "thermal_60x30",
        include_barcode: bool = True,
        include_remetente: bool = False
    ) -> bytes:
        """
        Gera etiqueta térmica (60x30mm ou 100x80mm)
        """
        label_config = LABEL_SIZES[size]
        width = label_config['width'] * mm
        height = label_config['height'] * mm

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(width, height))

        # Margens
        margin = 2 * mm
        current_y = height - margin

        # Configurar fonte
        font_size = 7 if size == "thermal_60x30" else 10
        line_height = font_size + 2

        # Formatar endereço
        address_lines = self._format_address(endereco, cliente_nome)

        # Desenhar endereço
        c.setFont("Helvetica-Bold", font_size)
        for i, line in enumerate(address_lines):
            if i == 0:  # Nome em destaque
                c.setFont("Helvetica-Bold", font_size + 1)
            else:
                c.setFont("Helvetica", font_size)

            current_y -= line_height
            # Truncar linha se muito longa
            max_chars = int((width - 2 * margin) / (font_size * 0.5))
            if len(line) > max_chars:
                line = line[:max_chars-3] + "..."
            c.drawString(margin, current_y, line)

        # Código de barras
        if include_barcode:
            try:
                barcode_img = CorreiosBarcode.generate_barcode_image(endereco['cep'])

                # Salvar imagem temporariamente
                temp_path = os.path.join(settings.LABELS_DIR, f"barcode_temp_{datetime.now().timestamp()}.png")
                barcode_img.save(temp_path)

                # Dimensões do código de barras
                if size == "thermal_60x30":
                    barcode_width = 40 * mm
                    barcode_height = 8 * mm
                    barcode_y = 2 * mm
                else:
                    barcode_width = 60 * mm
                    barcode_height = 12 * mm
                    barcode_y = 5 * mm

                c.drawImage(
                    temp_path,
                    margin,
                    barcode_y,
                    width=barcode_width,
                    height=barcode_height,
                    preserveAspectRatio=True
                )

                # Remover arquivo temporário
                os.remove(temp_path)
            except Exception as e:
                print(f"Erro ao gerar código de barras: {e}")

        # Remetente (apenas para etiquetas maiores)
        if include_remetente and self.remetente and size == "thermal_100x80":
            c.setFont("Helvetica", 6)
            remetente_lines = self._format_remetente()
            rem_y = 3 * mm
            for line in reversed(remetente_lines):
                c.drawRightString(width - margin, rem_y, line)
                rem_y += 7

        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    def generate_pimaco_sheet(
        self,
        labels_data: List[Dict[str, Any]],
        include_barcode: bool = True,
        include_remetente: bool = False
    ) -> bytes:
        """
        Gera folha A4 com etiquetas Pimaco (38,1x99mm - 14 etiquetas por folha)
        """
        config = LABEL_SIZES['pimaco_a4']

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)

        page_width, page_height = A4

        # Dimensões das etiquetas
        label_width = config['width'] * mm
        label_height = config['height'] * mm
        margin_top = config['margin_top'] * mm
        margin_left = config['margin_left'] * mm
        spacing_h = config['spacing_h'] * mm
        spacing_v = config['spacing_v'] * mm
        cols = config['columns']
        rows = config['rows']

        label_index = 0
        total_labels = len(labels_data)

        while label_index < total_labels:
            # Para cada etiqueta na página
            for row in range(rows):
                for col in range(cols):
                    if label_index >= total_labels:
                        break

                    data = labels_data[label_index]
                    label_index += 1

                    # Calcular posição da etiqueta
                    x = margin_left + col * (label_width + spacing_h)
                    y = page_height - margin_top - (row + 1) * label_height - row * spacing_v

                    # Desenhar retângulo da etiqueta (apenas para debug)
                    # c.rect(x, y, label_width, label_height)

                    # Desenhar conteúdo da etiqueta
                    self._draw_label_content(
                        c, x, y, label_width, label_height,
                        data['cliente_nome'],
                        data['endereco'],
                        include_barcode,
                        include_remetente,
                        font_size=8
                    )

            # Nova página se ainda houver etiquetas
            if label_index < total_labels:
                c.showPage()

        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    def generate_envelope(
        self,
        cliente_nome: str,
        endereco: Dict[str, Any],
        size: str = "envelope_dl",
        include_barcode: bool = True,
        include_remetente: bool = True
    ) -> bytes:
        """
        Gera impressão para envelope DL (110x220mm) ou C5 (162x229mm)
        """
        config = LABEL_SIZES[size]
        width = config['width'] * mm
        height = config['height'] * mm

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(width, height))

        margin = 10 * mm

        # Área do remetente (canto superior esquerdo)
        if include_remetente and self.remetente:
            c.setFont("Helvetica", 9)
            remetente_lines = self._format_remetente()
            rem_y = height - margin
            for line in remetente_lines:
                c.drawString(margin, rem_y, line)
                rem_y -= 12

        # Área do destinatário (centro-direita)
        dest_x = width * 0.35
        dest_y = height * 0.5

        address_lines = self._format_address(endereco, cliente_nome)

        font_size = 12 if size == "envelope_c5" else 10
        line_height = font_size + 4

        for i, line in enumerate(address_lines):
            if i == 0:
                c.setFont("Helvetica-Bold", font_size + 2)
            else:
                c.setFont("Helvetica", font_size)

            c.drawString(dest_x, dest_y, line)
            dest_y -= line_height

        # Código de barras
        if include_barcode:
            try:
                barcode_img = CorreiosBarcode.generate_barcode_image(endereco['cep'])

                temp_path = os.path.join(settings.LABELS_DIR, f"barcode_temp_{datetime.now().timestamp()}.png")
                barcode_img.save(temp_path)

                barcode_width = 70 * mm
                barcode_height = 15 * mm
                barcode_x = dest_x
                barcode_y = dest_y - 20 * mm

                c.drawImage(
                    temp_path,
                    barcode_x,
                    barcode_y,
                    width=barcode_width,
                    height=barcode_height,
                    preserveAspectRatio=True
                )

                os.remove(temp_path)
            except Exception as e:
                print(f"Erro ao gerar código de barras: {e}")

        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    def _draw_label_content(
        self,
        canvas_obj,
        x: float,
        y: float,
        width: float,
        height: float,
        cliente_nome: str,
        endereco: Dict[str, Any],
        include_barcode: bool,
        include_remetente: bool,
        font_size: int = 8
    ):
        """Desenha o conteúdo de uma etiqueta individual"""
        padding = 2 * mm
        line_height = font_size + 2
        current_y = y + height - padding

        # Formatar endereço
        address_lines = self._format_address(endereco, cliente_nome)

        # Desenhar endereço
        for i, line in enumerate(address_lines):
            if i == 0:
                canvas_obj.setFont("Helvetica-Bold", font_size)
            else:
                canvas_obj.setFont("Helvetica", font_size - 1)

            current_y -= line_height
            # Truncar se necessário
            max_chars = int((width - 2 * padding) / (font_size * 0.45))
            if len(line) > max_chars:
                line = line[:max_chars-3] + "..."
            canvas_obj.drawString(x + padding, current_y, line)

        # Código de barras
        if include_barcode:
            try:
                barcode_img = CorreiosBarcode.generate_barcode_image(endereco['cep'])
                temp_path = os.path.join(settings.LABELS_DIR, f"barcode_temp_{datetime.now().timestamp()}.png")
                barcode_img.save(temp_path)

                barcode_width = 50 * mm
                barcode_height = 8 * mm

                canvas_obj.drawImage(
                    temp_path,
                    x + padding,
                    y + padding,
                    width=barcode_width,
                    height=barcode_height,
                    preserveAspectRatio=True
                )

                os.remove(temp_path)
            except Exception:
                pass

    def generate_label(
        self,
        cliente_nome: str,
        endereco: Dict[str, Any],
        tipo_etiqueta: str,
        include_barcode: bool = True,
        include_remetente: bool = False
    ) -> bytes:
        """
        Método principal para gerar etiquetas de qualquer tipo
        """
        if tipo_etiqueta.startswith("thermal_"):
            return self.generate_thermal_label(
                cliente_nome, endereco, tipo_etiqueta,
                include_barcode, include_remetente
            )
        elif tipo_etiqueta == "pimaco_a4":
            return self.generate_pimaco_sheet(
                [{"cliente_nome": cliente_nome, "endereco": endereco}],
                include_barcode, include_remetente
            )
        elif tipo_etiqueta.startswith("envelope_"):
            return self.generate_envelope(
                cliente_nome, endereco, tipo_etiqueta,
                include_barcode, include_remetente
            )
        else:
            raise ValueError(f"Tipo de etiqueta não suportado: {tipo_etiqueta}")


# Instância global
label_generator = LabelGenerator()
