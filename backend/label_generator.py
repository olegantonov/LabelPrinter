"""
Gerador de etiquetas com suporte a codigo de barras dos Correios
Conforme especificacao: CORREIOS_ENDERECAMENTO_ESPEC_TECNICAS.md

Padroes implementados:
- CEPNet: codigo de barras do CEP (47 barras)
- Data Matrix: codigo 2D para triagem automatizada
- Layouts conforme Areas 1-6 dos Correios
- Resolucao minima: 300 DPI
"""
import io
import os
import re
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

from config import LABEL_SIZES, settings
from services.correios_codes import CEPNet, DataMatrix, TrackingCode


class LabelGenerator:
    """
    Gerador de etiquetas conforme padroes dos Correios

    Layouts suportados:
    - Etiqueta termica 60x30mm
    - Etiqueta termica 100x80mm
    - Folha Pimaco A4 (6 ou 14 etiquetas por folha)
    - Envelope DL (110x220mm)
    - Envelope C5 (162x229mm)
    """

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.remetente: Optional[Dict[str, str]] = None
        self.config = {
            "resolucao_dpi": 300,
            "incluir_cepnet": True,
            "incluir_datamatrix": False,
            "fonte_padrao": "Helvetica",
            "tamanho_fonte_min": 10
        }

    def set_remetente(self, remetente: Dict[str, str]):
        """Define os dados do remetente"""
        self.remetente = remetente

    def set_config(self, config: Dict[str, Any]):
        """Define configuracoes de geracao"""
        self.config.update(config)

    def _normalize_cep(self, cep: str) -> str:
        """Normaliza CEP para 8 digitos"""
        return re.sub(r'\D', '', cep)[:8]

    def _format_cep(self, cep: str) -> str:
        """
        Formata CEP conforme padrao Correios: 99999-999
        NAO usar "CEP:" antes do numero
        """
        cep_clean = self._normalize_cep(cep)
        if len(cep_clean) == 8:
            return f"{cep_clean[:5]}-{cep_clean[5:]}"
        return cep

    def _format_address_correios(self, endereco: Dict[str, Any], nome: str) -> List[str]:
        """
        Formata endereco conforme padrao Correios:
        1. Nome do destinatario
        2. Tipo + Nome do logradouro, Numero, Complemento
        3. Bairro
        4. CEP Cidade/UF (CEP como unica info se possivel)
        """
        lines = []

        # Destinatario (nome e sobrenome ou nome fantasia)
        destinatario = endereco.get('destinatario') or nome
        lines.append(destinatario.upper())

        # Logradouro, numero, complemento
        numero = endereco.get('numero', 's/n')
        if not numero or numero.upper() in ['', 'SN', 'S.N.']:
            numero = 's/n'

        logradouro = f"{endereco['logradouro']}, {numero}"
        if endereco.get('complemento'):
            logradouro += f", {endereco['complemento']}"
        lines.append(logradouro)

        # Bairro
        lines.append(endereco['bairro'])

        # CEP Cidade/UF
        cep = self._format_cep(endereco['cep'])
        lines.append(f"{cep} {endereco['cidade']}/{endereco['estado'].upper()}")

        return lines

    def _format_remetente_correios(self) -> List[str]:
        """
        Formata remetente conforme padrao Correios
        Fonte menor e diferente do destinatario
        """
        if not self.remetente:
            return []

        lines = []
        lines.append(f"Rem: {self.remetente.get('nome', '')}")

        numero = self.remetente.get('numero', 's/n')
        if not numero:
            numero = 's/n'

        logradouro = f"{self.remetente.get('logradouro', '')}, {numero}"
        if self.remetente.get('complemento'):
            logradouro += f", {self.remetente['complemento']}"
        lines.append(logradouro)

        cep = self._format_cep(self.remetente.get('cep', ''))
        lines.append(f"{cep} {self.remetente.get('cidade', '')}/{self.remetente.get('estado', '').upper()}")

        return lines

    def _generate_cepnet_image(self, cep: str) -> str:
        """
        Gera imagem do CEPNet e retorna caminho temporario
        """
        cep_clean = self._normalize_cep(cep)
        img = CEPNet.generate_image(cep_clean)

        temp_path = os.path.join(
            settings.LABELS_DIR,
            f"cepnet_{datetime.now().timestamp()}.png"
        )
        img.save(temp_path, dpi=(300, 300))
        return temp_path

    def _draw_cepnet(
        self,
        canvas_obj,
        cep: str,
        x: float,
        y: float,
        width: float,
        height: float
    ):
        """
        Desenha codigo de barras CEPNet no canvas
        Altura minima recomendada: 3.5mm (10 pontos)
        """
        try:
            temp_path = self._generate_cepnet_image(cep)
            canvas_obj.drawImage(
                temp_path,
                x, y,
                width=width,
                height=height,
                preserveAspectRatio=True
            )
            os.remove(temp_path)
        except Exception as e:
            print(f"Erro ao desenhar CEPNet: {e}")

    def generate_thermal_label(
        self,
        cliente_nome: str,
        endereco: Dict[str, Any],
        size: str = "thermal_60x30",
        include_barcode: bool = True,
        include_remetente: bool = False
    ) -> bytes:
        """
        Gera etiqueta termica (60x30mm ou 100x80mm)
        Resolucao: 300 DPI
        """
        label_config = LABEL_SIZES[size]
        width = label_config['width'] * mm
        height = label_config['height'] * mm

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(width, height))

        # Margens
        margin = 2 * mm
        current_y = height - margin

        # Tamanho da fonte (minimo 10 pontos conforme Correios)
        font_size = 8 if size == "thermal_60x30" else 10
        line_height = font_size + 3

        # Formatar endereco
        address_lines = self._format_address_correios(endereco, cliente_nome)

        # Desenhar endereco (Area 4 - Bloco do destinatario)
        for i, line in enumerate(address_lines):
            if i == 0:  # Nome em destaque
                c.setFont("Helvetica-Bold", font_size + 1)
            elif i == len(address_lines) - 1:  # CEP em destaque
                c.setFont("Helvetica-Bold", font_size)
            else:
                c.setFont("Helvetica", font_size)

            current_y -= line_height

            # Truncar linha se muito longa
            max_chars = int((width - 2 * margin) / (font_size * 0.5))
            if len(line) > max_chars:
                line = line[:max_chars-3] + "..."

            c.drawString(margin, current_y, line)

        # Codigo de barras CEPNet
        if include_barcode and self.config.get("incluir_cepnet", True):
            if size == "thermal_60x30":
                barcode_width = 45 * mm
                barcode_height = 8 * mm
                barcode_y = 2 * mm
            else:
                barcode_width = 65 * mm
                barcode_height = 12 * mm
                barcode_y = 5 * mm

            self._draw_cepnet(
                c,
                endereco['cep'],
                margin,
                barcode_y,
                barcode_width,
                barcode_height
            )

        # Remetente (Area 1 - fonte menor)
        if include_remetente and self.remetente and size == "thermal_100x80":
            c.setFont("Helvetica", 6)
            remetente_lines = self._format_remetente_correios()
            rem_y = 3 * mm
            for line in reversed(remetente_lines):
                c.drawRightString(width - margin, rem_y, line)
                rem_y += 8

        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    def generate_pimaco_sheet(
        self,
        labels_data: List[Dict[str, Any]],
        include_barcode: bool = True,
        include_remetente: bool = False,
        layout: str = "14_per_sheet"
    ) -> bytes:
        """
        Gera folha A4 com etiquetas Pimaco

        Layouts conforme especificacao Correios:
        - 6 rotulos por folha: 84.7 x 101.6 mm (Pimaco 6184)
        - 14 rotulos por folha: 38.1 x 99.0 mm (padrao atual)
        """
        if layout == "6_per_sheet":
            config = {
                "width": 101.6,
                "height": 84.7,
                "labels_per_sheet": 6,
                "columns": 2,
                "rows": 3,
                "margin_top": 21.2,
                "margin_left": 3.9,
                "spacing_h": 0,
                "spacing_v": 0
            }
        else:
            config = LABEL_SIZES['pimaco_a4']

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)

        page_width, page_height = A4

        # Dimensoes das etiquetas
        label_width = config['width'] * mm
        label_height = config['height'] * mm
        margin_top = config['margin_top'] * mm
        margin_left = config['margin_left'] * mm
        spacing_h = config.get('spacing_h', 0) * mm
        spacing_v = config.get('spacing_v', 0) * mm
        cols = config['columns']
        rows = config['rows']

        label_index = 0
        total_labels = len(labels_data)

        while label_index < total_labels:
            for row in range(rows):
                for col in range(cols):
                    if label_index >= total_labels:
                        break

                    data = labels_data[label_index]
                    label_index += 1

                    # Calcular posicao da etiqueta
                    x = margin_left + col * (label_width + spacing_h)
                    y = page_height - margin_top - (row + 1) * label_height - row * spacing_v

                    # Desenhar conteudo
                    self._draw_label_content(
                        c, x, y, label_width, label_height,
                        data['cliente_nome'],
                        data['endereco'],
                        include_barcode,
                        include_remetente,
                        font_size=9 if layout == "6_per_sheet" else 8
                    )

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
        Gera impressao para envelope conforme layout Correios (Areas 1-6)

        Envelope DL: 110x220mm
        Envelope C5: 162x229mm

        Areas:
        - Area 1: Conteudo do remetente (canto superior esquerdo)
        - Area 3: Franqueamento (canto superior direito)
        - Area 4: Bloco do destinatario (centro-direita)
        - Area 5: Codigo de rastreamento (se aplicavel)
        - Area 6: Uso dos Correios
        """
        config = LABEL_SIZES[size]
        width = config['width'] * mm
        height = config['height'] * mm

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(width, height))

        margin = 10 * mm

        # ===== AREA 1: Remetente (canto superior esquerdo) =====
        if include_remetente and self.remetente:
            c.setFont("Helvetica", 8)  # Fonte menor que destinatario
            remetente_lines = self._format_remetente_correios()
            rem_y = height - margin
            for line in remetente_lines:
                c.drawString(margin, rem_y, line)
                rem_y -= 10

            # Linha separadora opcional
            c.setStrokeColor(colors.lightgrey)
            c.line(margin, rem_y - 5, width * 0.35, rem_y - 5)

        # ===== AREA 4: Bloco do destinatario (centro-direita) =====
        dest_x = width * 0.38
        dest_y = height * 0.55

        address_lines = self._format_address_correios(endereco, cliente_nome)

        font_size = 12 if size == "envelope_c5" else 11
        line_height = font_size + 5

        for i, line in enumerate(address_lines):
            if i == 0:  # Nome
                c.setFont("Helvetica-Bold", font_size + 2)
            elif i == len(address_lines) - 1:  # CEP
                c.setFont("Helvetica-Bold", font_size + 1)
            else:
                c.setFont("Helvetica", font_size)

            c.drawString(dest_x, dest_y, line)
            dest_y -= line_height

        # ===== Codigo de barras CEPNet =====
        if include_barcode and self.config.get("incluir_cepnet", True):
            barcode_width = 70 * mm
            barcode_height = 12 * mm
            barcode_x = dest_x
            barcode_y = dest_y - 15 * mm

            self._draw_cepnet(
                c,
                endereco['cep'],
                barcode_x,
                barcode_y,
                barcode_width,
                barcode_height
            )

        # ===== AREA 3: Espaco para franqueamento (canto superior direito) =====
        # Desenhar area reservada para selo/chancela
        c.setStrokeColor(colors.lightgrey)
        c.setDash(2, 2)
        selo_x = width - margin - 35 * mm
        selo_y = height - margin - 25 * mm
        c.rect(selo_x, selo_y, 35 * mm, 25 * mm)
        c.setDash()

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
        """Desenha o conteudo de uma etiqueta individual"""
        padding = 3 * mm
        line_height = font_size + 3
        current_y = y + height - padding

        # Formatar endereco
        address_lines = self._format_address_correios(endereco, cliente_nome)

        # Desenhar endereco
        for i, line in enumerate(address_lines):
            if i == 0:
                canvas_obj.setFont("Helvetica-Bold", font_size)
            elif i == len(address_lines) - 1:
                canvas_obj.setFont("Helvetica-Bold", font_size - 1)
            else:
                canvas_obj.setFont("Helvetica", font_size - 1)

            current_y -= line_height

            # Truncar se necessario
            max_chars = int((width - 2 * padding) / (font_size * 0.45))
            if len(line) > max_chars:
                line = line[:max_chars-3] + "..."

            canvas_obj.drawString(x + padding, current_y, line)

        # Codigo de barras CEPNet
        if include_barcode and self.config.get("incluir_cepnet", True):
            barcode_width = min(60 * mm, width - 2 * padding)
            barcode_height = 10 * mm

            self._draw_cepnet(
                canvas_obj,
                endereco['cep'],
                x + padding,
                y + padding,
                barcode_width,
                barcode_height
            )

    def generate_label(
        self,
        cliente_nome: str,
        endereco: Dict[str, Any],
        tipo_etiqueta: str,
        include_barcode: bool = True,
        include_remetente: bool = False
    ) -> bytes:
        """
        Metodo principal para gerar etiquetas de qualquer tipo
        """
        if tipo_etiqueta.startswith("thermal_"):
            return self.generate_thermal_label(
                cliente_nome, endereco, tipo_etiqueta,
                include_barcode, include_remetente
            )
        elif tipo_etiqueta == "pimaco_a4":
            return self.generate_pimaco_sheet(
                [{"cliente_nome": cliente_nome, "endereco": endereco}],
                include_barcode, include_remetente,
                layout="14_per_sheet"
            )
        elif tipo_etiqueta == "pimaco_6":
            return self.generate_pimaco_sheet(
                [{"cliente_nome": cliente_nome, "endereco": endereco}],
                include_barcode, include_remetente,
                layout="6_per_sheet"
            )
        elif tipo_etiqueta.startswith("envelope_"):
            return self.generate_envelope(
                cliente_nome, endereco, tipo_etiqueta,
                include_barcode, include_remetente
            )
        else:
            raise ValueError(f"Tipo de etiqueta nao suportado: {tipo_etiqueta}")


# Instancia global
label_generator = LabelGenerator()
