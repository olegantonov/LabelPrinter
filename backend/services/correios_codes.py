"""
Codigos de barras padrao Correios
Conforme especificacao: CORREIOS_ENDERECAMENTO_ESPEC_TECNICAS.md

CEPNet: Codigo de barras do CEP (47 barras)
Data Matrix: Codigo 2D com informacoes de triagem
"""
import io
import re
from typing import Optional, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# Importar pylabels para Data Matrix se disponivel
try:
    from pylibdmtx.pylibdmtx import encode as dmtx_encode
    DATAMATRIX_AVAILABLE = True
except ImportError:
    DATAMATRIX_AVAILABLE = False


class CEPNet:
    """
    Gerador de codigo de barras CEPNet (padrao Correios)

    Especificacoes:
    - Representa os 8 digitos do CEP + digito verificador
    - 47 barras totais (5 barras por digito + 2 delimitadoras)
    - Cada digito: 2 barras altas + 3 barras baixas
    - Altura minima: 3mm (9 pontos), recomendado: 3.5mm (10 pontos)
    """

    # Codificacao CEPNet: cada digito e representado por 5 barras
    # A = barra alta, B = barra baixa
    # Formato: posicoes das 2 barras altas entre as 5
    DIGIT_ENCODING = {
        '0': 'BBAAB',  # 0: barras altas nas posicoes 3,4
        '1': 'BABAB',  # 1: barras altas nas posicoes 1,3
        '2': 'BABBA',  # 2: barras altas nas posicoes 1,4
        '3': 'BAABB',  # 3: barras altas nas posicoes 2,4
        '4': 'ABBAB',  # 4: barras altas nas posicoes 0,3
        '5': 'ABBBA',  # 5: barras altas nas posicoes 0,4
        '6': 'ABABB',  # 6: barras altas nas posicoes 1,2
        '7': 'AABBB',  # 7: barras altas nas posicoes 0,2
        '8': 'AABAB',  # 8: barras altas nas posicoes 0,1
        '9': 'AABBA',  # 9: barras altas nas posicoes 0,1 (alternativo)
    }

    @staticmethod
    def calculate_check_digit(cep: str) -> int:
        """
        Calcula digito verificador do CEP (padrao Correios)

        Algoritmo:
        1. Soma os 8 digitos do CEP
        2. Encontra o multiplo de 10 imediatamente superior
        3. Subtrai a soma desse multiplo

        Exemplo: CEP 71010050
        - Soma: 7+1+0+1+0+0+5+0 = 14
        - Multiplo de 10 superior: 20
        - Verificador: 20-14 = 6
        """
        cep_digits = [int(d) for d in re.sub(r'\D', '', cep)[:8]]

        if len(cep_digits) != 8:
            raise ValueError("CEP deve ter 8 digitos")

        soma = sum(cep_digits)
        multiplo_superior = ((soma // 10) + 1) * 10

        # Se soma ja for multiplo de 10, usar o proximo
        if soma % 10 == 0:
            return 0

        return multiplo_superior - soma

    @staticmethod
    def format_cep_with_check(cep: str) -> str:
        """Retorna CEP com digito verificador"""
        cep_clean = re.sub(r'\D', '', cep)[:8]
        check = CEPNet.calculate_check_digit(cep_clean)
        return f"{cep_clean}{check}"

    @staticmethod
    def generate_barcode_pattern(cep: str) -> str:
        """
        Gera padrao de barras do CEPNet

        Retorna string com 'A' (barra alta) e 'B' (barra baixa)
        Total: 47 caracteres (1 inicio + 9 digitos * 5 + 1 fim)
        """
        cep_clean = re.sub(r'\D', '', cep)[:8]
        check_digit = CEPNet.calculate_check_digit(cep_clean)
        full_code = cep_clean + str(check_digit)

        # Barra de inicio
        pattern = 'A'

        # Codificar cada digito
        for digit in full_code:
            pattern += CEPNet.DIGIT_ENCODING[digit]

        # Barra de fim
        pattern += 'A'

        return pattern

    @staticmethod
    def generate_image(
        cep: str,
        width: int = 200,
        height: int = 40,
        bar_width: int = 2,
        include_text: bool = True
    ) -> Image.Image:
        """
        Gera imagem do codigo de barras CEPNet

        Args:
            cep: CEP de 8 digitos
            width: Largura da imagem
            height: Altura total da imagem
            bar_width: Largura de cada barra em pixels
            include_text: Incluir texto do CEP abaixo
        """
        pattern = CEPNet.generate_barcode_pattern(cep)

        # Calcular dimensoes
        num_bars = len(pattern)
        actual_width = num_bars * bar_width + 20  # Margem de 10px cada lado
        bar_area_height = height - 15 if include_text else height - 5

        # Altura das barras
        high_bar_height = bar_area_height
        low_bar_height = int(bar_area_height * 0.5)

        # Criar imagem
        img = Image.new('RGB', (actual_width, height), 'white')
        draw = ImageDraw.Draw(img)

        # Desenhar barras
        x = 10  # Margem esquerda
        for bar_type in pattern:
            bar_height = high_bar_height if bar_type == 'A' else low_bar_height
            y_start = 2
            y_end = y_start + bar_height

            draw.rectangle(
                [x, y_start, x + bar_width - 1, y_end],
                fill='black'
            )
            x += bar_width

        # Adicionar texto
        if include_text:
            cep_formatted = CEPNet.format_cep_with_check(cep)
            cep_display = f"{cep_formatted[:5]}-{cep_formatted[5:8]} ({cep_formatted[8]})"

            # Tentar usar fonte, fallback para padrao
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 10)
            except:
                font = ImageFont.load_default()

            text_bbox = draw.textbbox((0, 0), cep_display, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = (actual_width - text_width) // 2
            text_y = height - 12

            draw.text((text_x, text_y), cep_display, fill='black', font=font)

        return img


class DataMatrix:
    """
    Gerador de Data Matrix padrao Correios

    Estrutura (156 caracteres):
    1. CEP destino (8)
    2. Complemento CEP destino (5) - numero do imovel ou 00000
    3. CEP origem/devolucao (8)
    4. Complemento CEP origem (5)
    5. Validador CEP destino (1)
    6. IDV (2) - tipo de servico
    7. CIF (34)
    8. Servicos adicionais (10)
    9. Codigo servico principal (5)
    10. Campo reserva (15) - preencher com zeros
    11. CNAE (9)
    12. Codigo rastreamento (13)
    13. Campo livre cliente (ate 54)
    14. Indicador fim de dados (1) - caractere |
    """

    # Codigos IDV (tipo de servico)
    IDV_CODES = {
        "FAC_SIMPLES": "01",
        "CARTA_SIMPLES": "03",
        "E_CARTA_SIMPLES": "04",
        "FAC_REGISTRADO": "16",
        "CARTA_REGISTRADA": "17",
        "CARTA_VIA_INTERNET": "27",
        "E_CARTA_REGISTRADO": "28"
    }

    # Servicos adicionais (3 digitos cada)
    SERVICOS_ADICIONAIS = {
        "AR": "001",  # Aviso de Recebimento
        "MP": "002",  # Mao Propria
        "VD": "003",  # Valor Declarado
        "DD": "004",  # Devolucao de Documentos
    }

    @staticmethod
    def calculate_cep_validator(cep: str) -> str:
        """
        Calcula validador do CEP (mesmo algoritmo do CEPNet)
        """
        return str(CEPNet.calculate_check_digit(cep))

    @staticmethod
    def format_numero(numero: str) -> str:
        """
        Formata numero do imovel para complemento CEP (5 digitos)
        Se SN ou vazio, retorna 00000
        """
        if not numero or numero.upper() in ['SN', 'S/N', 'S.N.']:
            return "00000"

        # Extrair apenas digitos
        digits = re.sub(r'\D', '', numero)
        return digits[:5].zfill(5)

    @staticmethod
    def format_servicos_adicionais(servicos: list) -> str:
        """
        Formata campo de servicos adicionais (10 digitos)
        Servicos em ordem crescente, completar com zeros
        """
        codes = []
        for servico in servicos:
            if servico.upper() in DataMatrix.SERVICOS_ADICIONAIS:
                codes.append(DataMatrix.SERVICOS_ADICIONAIS[servico.upper()])

        # Ordenar e juntar
        codes.sort()
        result = ''.join(codes)

        # Completar com zeros ate 10 digitos
        return result.ljust(10, '0')

    @staticmethod
    def generate_content(
        cep_destino: str,
        numero_destino: str,
        cep_origem: str,
        numero_origem: str,
        idv: str = "03",
        cif: str = "",
        servicos_adicionais: list = None,
        codigo_servico: str = "",
        cnae: str = "",
        codigo_rastreamento: str = "",
        campo_livre: str = ""
    ) -> str:
        """
        Gera conteudo do Data Matrix conforme especificacao Correios
        """
        # Normalizar CEPs
        cep_dest = re.sub(r'\D', '', cep_destino)[:8].ljust(8, '0')
        cep_orig = re.sub(r'\D', '', cep_origem)[:8].ljust(8, '0')

        # Montar campos
        campos = []

        # 1. CEP destino (8)
        campos.append(cep_dest)

        # 2. Complemento CEP destino (5)
        campos.append(DataMatrix.format_numero(numero_destino))

        # 3. CEP origem (8)
        campos.append(cep_orig)

        # 4. Complemento CEP origem (5)
        campos.append(DataMatrix.format_numero(numero_origem))

        # 5. Validador CEP destino (1)
        campos.append(DataMatrix.calculate_cep_validator(cep_dest))

        # 6. IDV (2)
        campos.append(idv[:2].zfill(2))

        # 7. CIF (34)
        campos.append(cif[:34].ljust(34, '0'))

        # 8. Servicos adicionais (10)
        servicos = servicos_adicionais or []
        campos.append(DataMatrix.format_servicos_adicionais(servicos))

        # 9. Codigo servico principal (5)
        campos.append(codigo_servico[:5].ljust(5, '0'))

        # 10. Campo reserva (15 zeros)
        campos.append('0' * 15)

        # 11. CNAE (9)
        cnae_clean = re.sub(r'\D', '', cnae)[:9].ljust(9, '0')
        campos.append(cnae_clean)

        # 12. Codigo rastreamento (13)
        campos.append(codigo_rastreamento[:13].ljust(13, ' '))

        # 13. Campo livre (ate 54)
        campos.append(campo_livre[:54])

        # 14. Indicador fim de dados
        campos.append('|')

        return ''.join(campos)

    @staticmethod
    def generate_image(
        content: str,
        size: str = "26x26"
    ) -> Optional[Image.Image]:
        """
        Gera imagem do Data Matrix

        Tamanhos padrao Correios:
        - 26x26 (9.1 x 9.1 mm)
        - 32x32 (11.2 x 11.2 mm)
        - 36x36 (12.6 x 12.6 mm)
        """
        if not DATAMATRIX_AVAILABLE:
            return None

        try:
            encoded = dmtx_encode(content.encode('utf-8'))
            img = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
            return img
        except Exception as e:
            print(f"Erro ao gerar Data Matrix: {e}")
            return None


class TrackingCode:
    """
    Codigo de rastreamento (texto + UCC-128)

    Formato: SS 123 456 789 BR
    - SS: Sigla do servico (2 letras)
    - 9 digitos numericos
    - BR: Pais de origem
    """

    @staticmethod
    def format_tracking(code: str) -> str:
        """
        Formata codigo de rastreamento para exibicao
        JC123456789BR -> JC 123 456 789 BR
        """
        code = code.upper().strip()

        if len(code) != 13:
            return code

        return f"{code[:2]} {code[2:5]} {code[5:8]} {code[8:11]} {code[11:]}"

    @staticmethod
    def validate_tracking(code: str) -> bool:
        """Valida formato do codigo de rastreamento"""
        code = re.sub(r'\s', '', code).upper()
        return bool(re.match(r'^[A-Z]{2}\d{9}[A-Z]{2}$', code))

    @staticmethod
    def generate_barcode(code: str) -> Optional[Image.Image]:
        """
        Gera codigo de barras UCC-128 para rastreamento

        Dimensoes minimas: 66 x 15 mm
        - 56mm largura
        - 15mm altura
        - 5mm margem horizontal
        """
        try:
            import barcode
            from barcode.writer import ImageWriter

            code_clean = re.sub(r'\s', '', code).upper()

            writer = ImageWriter()
            writer.set_options({
                'module_width': 0.4,
                'module_height': 15,
                'quiet_zone': 5,
                'font_size': 10,
                'text_distance': 3,
                'write_text': True
            })

            code128 = barcode.get_barcode_class('code128')
            barcode_obj = code128(code_clean, writer=writer)

            buffer = io.BytesIO()
            barcode_obj.write(buffer)
            buffer.seek(0)

            return Image.open(buffer)
        except Exception as e:
            print(f"Erro ao gerar codigo de barras: {e}")
            return None
