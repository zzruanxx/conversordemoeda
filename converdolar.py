import sys
from PyQt5.QtCore import Qt, QEasingCurve, QPropertyAnimation, QRect, QTimer
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
)
from PyQt5.QtGui import QFont, QColor, QPalette, QDoubleValidator

# Exchange rate constants (1 USD =)
COP_TO_USD = 0.00024  # Colombian Peso to USD
PEN_TO_USD = 0.27     # Peruvian Sol to USD
BRL_TO_USD = 0.18     # Brazilian Real to USD

# Cryptocurrency exchange rates (to USD) - approximate reference values
BTC_TO_USD = 60000.00  # Bitcoin to USD
ETH_TO_USD = 3000.00   # Ethereum to USD

# Exchange rate display (for info label)
USD_TO_COP = 4166.67  # USD to Colombian Peso
USD_TO_PEN = 3.70     # USD to Peruvian Sol
USD_TO_BRL = 5.55     # USD to Brazilian Real

# UI Gradient color constants
GRADIENT_PURPLE_VIOLET = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #667eea, stop:1 #764ba2)"
GRADIENT_PINK_RED = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f093fb, stop:1 #f5576c)"
GRADIENT_CYAN_TURQUOISE = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4facfe, stop:1 #00f2fe)"
GRADIENT_GREEN = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #56ab2f, stop:1 #a8e063)"
GRADIENT_GREEN_HOVER = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a9628, stop:1 #95c956)"
GRADIENT_ORANGE_GOLD = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f7971e, stop:1 #ffd200)"
GRADIENT_INDIGO_BLUE = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #667eea, stop:1 #4facfe)"
GRADIENT_GRAY = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #434343, stop:1 #000000)"
GRADIENT_GRAY_HOVER = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #525252, stop:1 #1a1a1a)"


def convert_amounts(pesos=0.0, soles=0.0, reais=0.0, btc=0.0, eth=0.0):
    """
    Backend conversion helper that returns USD amounts and total.

    Args:
        pesos (float | int | str): Valor em Pesos Colombianos (COP).
        soles (float | int | str): Valor em Soles Peruanos (PEN).
        reais (float | int | str): Valor em Reais Brasileiros (BRL).
        btc (float | int | str): Quantidade em Bitcoin (BTC).
        eth (float | int | str): Quantidade em Ethereum (ETH).

    Returns:
        dict: Estrutura contendo os valores originais em ``inputs``, os valores
        convertidos para USD em ``usd`` e o ``total`` em USD somando todas as moedas.

    Example:
        >>> convert_amounts(pesos=10000, btc=0.1)["usd"]["btc"]
        6000.0  # considerando BTC_TO_USD = 60000.0

    Raises:
        ValueError: when any provided value is not convertible to float (e.g., invalid strings or None) or negative.
    """
    fields = {
        "pesos": ("Pesos Colombianos (COP)", pesos),
        "soles": ("Soles Peruanos (PEN)", soles),
        "reais": ("Reais Brasileiros (BRL)", reais),
        "btc": ("Bitcoin (BTC)", btc),
        "eth": ("Ethereum (ETH)", eth),
    }
    values = {}
    for key, (name, raw) in fields.items():
        try:
            numeric = float(raw)
        except (TypeError, ValueError):
            raise ValueError(f"Valor inválido '{raw}' para {name}")
        if numeric < 0:
            raise ValueError(f"Valor negativo {numeric} não permitido para {name}")
        values[key] = numeric

    usd_values = {
        "pesos": values["pesos"] * COP_TO_USD,
        "soles": values["soles"] * PEN_TO_USD,
        "reais": values["reais"] * BRL_TO_USD,
        "btc": values["btc"] * BTC_TO_USD,
        "eth": values["eth"] * ETH_TO_USD,
    }
    total = sum(usd_values.values())
    return {"inputs": values, "usd": usd_values, "total": total}


class AnimatedInput(QFrame):
    def __init__(self, label_text, color, placeholder, parent=None):
        super().__init__(parent)
        self.color = color
        self.setStyleSheet(f"background: {color}; border-radius: 18px; padding: 4px;")
        self.setMaximumHeight(110)
        self.setMinimumHeight(110)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        self.label = QLabel(label_text)
        self.label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.label.setStyleSheet("color: #ffffff; background: transparent;")
        self.input = QLineEdit()
        self.input.setFont(QFont("Segoe UI", 15))
        self.input.setPlaceholderText(placeholder)
        self.input.setStyleSheet(
            "background: #ffffff; border: 3px solid transparent; border-radius: 12px; padding: 12px 16px; color: #2c3e50;"
        )
        self.input.setClearButtonEnabled(True)
        validator = QDoubleValidator(0.0, 1e12, 2, self.input)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.input.setValidator(validator)
        self.input.textChanged.connect(self.validateInput)
        layout.addWidget(self.label)
        layout.addWidget(self.input)
        self.setLayout(layout)

    def validateInput(self):
        text = self.input.text()
        if text and text.strip():
            try:
                float(text.replace(',', '.'))
                self.input.setStyleSheet(
                    "background: #ffffff; border: 3px solid #27ae60; border-radius: 12px; padding: 12px 16px; color: #2c3e50;"
                )
            except ValueError:
                self.input.setStyleSheet(
                    "background: #ffffff; border: 3px solid #e74c3c; border-radius: 12px; padding: 12px 16px; color: #2c3e50;"
                )
        else:
            self.input.setStyleSheet(
                "background: #ffffff; border: 3px solid transparent; border-radius: 12px; padding: 12px 16px; color: #2c3e50;"
            )

    def animateIn(self, delay=0):
        def start_anim():
            self.anim = QPropertyAnimation(self, b"geometry")
            start_rect = QRect(self.x(), self.y() + 100, self.width(), self.height())
            end_rect = QRect(self.x(), self.y(), self.width(), self.height())
            self.anim.setStartValue(start_rect)
            self.anim.setEndValue(end_rect)
            self.anim.setDuration(800)
            self.anim.setEasingCurve(QEasingCurve.OutBack)
            self.anim.start()
        if delay > 0:
            QTimer.singleShot(delay, start_anim)
        else:
            start_anim()

class AnimatedButton(QPushButton):
    def __init__(self, text, color, hover_color, parent=None):
        super().__init__(text, parent)
        self.color = color
        self.hover_color = hover_color
        self.setFont(QFont("Segoe UI", 15, QFont.Bold))
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"background: {color}; color: #ffffff; border-radius: 14px; padding: 16px 32px; border: none; font-weight: 600;"
        )
        self.setMinimumHeight(56)

    def enterEvent(self, event):
        self.setStyleSheet(
            f"background: {self.hover_color}; color: #ffffff; border-radius: 14px; padding: 16px 32px; border: none; font-weight: 600;"
        )
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(
            f"background: {self.color}; color: #ffffff; border-radius: 14px; padding: 16px 32px; border: none; font-weight: 600;"
        )
        super().leaveEvent(event)

    def animateIn(self, delay=0):
        def start_anim():
            self.anim = QPropertyAnimation(self, b"geometry")
            start_rect = QRect(self.x() - 200, self.y(), self.width(), self.height())
            end_rect = QRect(self.x(), self.y(), self.width(), self.height())
            self.anim.setStartValue(start_rect)
            self.anim.setEndValue(end_rect)
            self.anim.setDuration(700)
            self.anim.setEasingCurve(QEasingCurve.OutBack)
            self.anim.start()
        if delay > 0:
            QTimer.singleShot(delay, start_anim)
        else:
            start_anim()

class ResultLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setFont(QFont("Segoe UI", 14))
        self.setStyleSheet(
            "color: #1e3a28; background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #d4edda, stop:1 #c3e6cb); "
            "border-radius: 16px; padding: 20px; border: 3px solid #66bb6a; font-weight: 500;"
        )
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(120)
        self.setWordWrap(True)
        self.hide()

    def showAnimated(self, text):
        self.setText(text)
        self.setWindowOpacity(0)
        self.show()
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.setDuration(600)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.anim.start()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("💸 Conversor de Moedas")
        self.setGeometry(100, 100, 550, 950)
        self.setMinimumSize(500, 850)
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#0f1419"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(18)

        # Title with subtitle
        title_container = QVBoxLayout()
        title_container.setSpacing(8)
        self.title = QLabel("💸 Conversor de Moedas")
        self.title.setFont(QFont("Segoe UI", 28, QFont.Bold))
        self.title.setStyleSheet("color: #ffffff;")
        self.title.setAlignment(Qt.AlignCenter)
        
        self.subtitle = QLabel("Converta moedas e criptomoedas para dólar americano")
        self.subtitle.setFont(QFont("Segoe UI", 12))
        self.subtitle.setStyleSheet("color: #8b92a8; font-weight: 400;")
        self.subtitle.setAlignment(Qt.AlignCenter)
        
        title_container.addWidget(self.title)
        title_container.addWidget(self.subtitle)
        layout.addLayout(title_container)
        layout.addSpacing(16)

        # Currency inputs with placeholders
        self.pesos_input = AnimatedInput("🇨🇴 Pesos Colombianos (COP)", GRADIENT_PURPLE_VIOLET, "Ex: 10000")
        self.soles_input = AnimatedInput("🇵🇪 Sol Peruano (PEN)", GRADIENT_PINK_RED, "Ex: 100")
        self.reais_input = AnimatedInput("🇧🇷 Real Brasileiro (BRL)", GRADIENT_CYAN_TURQUOISE, "Ex: 50")

        # Cryptocurrency inputs
        self.btc_input = AnimatedInput("₿ Bitcoin (BTC)", GRADIENT_ORANGE_GOLD, "Ex: 0.5")
        self.eth_input = AnimatedInput("⟠ Ethereum (ETH)", GRADIENT_INDIGO_BLUE, "Ex: 2.0")

        layout.addWidget(self.pesos_input)
        layout.addWidget(self.soles_input)
        layout.addWidget(self.reais_input)
        layout.addWidget(self.btc_input)
        layout.addWidget(self.eth_input)

        # Buttons layout
        button_layout = QVBoxLayout()
        button_layout.setSpacing(14)
        
        self.button = AnimatedButton("💱 Converter para Dólar (USD)", GRADIENT_GREEN, GRADIENT_GREEN_HOVER)
        self.button.clicked.connect(self.convert)
        button_layout.addWidget(self.button)
        
        self.clear_button = AnimatedButton("🔄 Limpar Todos os Campos", GRADIENT_GRAY, GRADIENT_GRAY_HOVER)
        self.clear_button.clicked.connect(self.clear_fields)
        button_layout.addWidget(self.clear_button)
        
        layout.addLayout(button_layout)

        self.hint_label = QLabel("💡 Dica: pressione Enter em qualquer campo para converter rapidamente.")
        self.hint_label.setFont(QFont("Segoe UI", 10))
        self.hint_label.setStyleSheet("color: #9aa5b1; padding: 6px 8px;")
        self.hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.hint_label)

        # Info label for exchange rates
        self.info_label = QLabel(
            f"📊 1 USD = {USD_TO_COP:.2f} COP | {USD_TO_PEN:.2f} PEN | {USD_TO_BRL:.2f} BRL\n"
            f"₿ 1 BTC = ${BTC_TO_USD:,.2f} | ⟠ 1 ETH = ${ETH_TO_USD:,.2f}"
        )
        self.info_label.setFont(QFont("Segoe UI", 10))
        self.info_label.setStyleSheet("color: #6c7a89; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 8px;")
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)

        self.result_label = ResultLabel()
        layout.addWidget(self.result_label)
        
        layout.addStretch()
        self.setLayout(layout)

        # Animate elements on start (like GSAP stagger)
        QTimer.singleShot(100, self.animStart)

        # Atalhos de teclado
        for inp in (self.pesos_input.input, self.soles_input.input, self.reais_input.input, self.btc_input.input, self.eth_input.input):
            inp.returnPressed.connect(self.convert)

    def clear_fields(self):
        """Clear all input fields and hide result"""
        self.pesos_input.input.clear()
        self.soles_input.input.clear()
        self.reais_input.input.clear()
        self.btc_input.input.clear()
        self.eth_input.input.clear()
        self.result_label.hide()
        self.pesos_input.input.setFocus()

    def animStart(self):
        self.title.setWindowOpacity(0)
        anim = QPropertyAnimation(self.title, b"windowOpacity")
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setDuration(700)
        anim.start()
        
        self.subtitle.setWindowOpacity(0)
        anim2 = QPropertyAnimation(self.subtitle, b"windowOpacity")
        anim2.setStartValue(0)
        anim2.setEndValue(1)
        anim2.setDuration(700)
        anim2.start()
        
        self.pesos_input.animateIn(0)
        self.soles_input.animateIn(200)
        self.reais_input.animateIn(400)
        self.btc_input.animateIn(500)
        self.eth_input.animateIn(600)
        self.button.animateIn(700)
        self.clear_button.animateIn(800)

    def _parse_currency_input(self, input_text):
        """Parse and validate currency input, returning float value or 0 if invalid"""
        try:
            if input_text and input_text.strip():
                return float(input_text.replace(',', '.'))
        except (ValueError, AttributeError):
            pass
        return 0.0

    def convert(self):
        # Validate and parse inputs
        pesos = self._parse_currency_input(self.pesos_input.input.text())
        soles = self._parse_currency_input(self.soles_input.input.text())
        reais = self._parse_currency_input(self.reais_input.input.text())
        btc = self._parse_currency_input(self.btc_input.input.text())
        eth = self._parse_currency_input(self.eth_input.input.text())
        
        try:
            conversion = convert_amounts(pesos, soles, reais, btc, eth)
        except ValueError:
            self.result_label.setStyleSheet(
                "color: #721c24; background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f8d7da, stop:1 #f5c6cb); "
                "border-radius: 16px; padding: 20px; border: 3px solid #f44336; font-weight: 500;"
            )
            self.result_label.showAnimated(
                "<span style='color: #c0392b; font-weight: bold; font-size: 15px;'>⚠️ Valores inválidos. Por favor, insira apenas números positivos.</span>"
            )
            return

        # UI requirement: ensure the user provided at least one positive value
        has_valid_input = any(value > 0 for value in conversion["inputs"].values())

        if not has_valid_input:
            self.result_label.setStyleSheet(
                "color: #721c24; background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f8d7da, stop:1 #f5c6cb); "
                "border-radius: 16px; padding: 20px; border: 3px solid #f44336; font-weight: 500;"
            )
            self.result_label.showAnimated(
                "<span style='color: #c0392b; font-weight: bold; font-size: 15px;'>⚠️ Por favor, insira pelo menos um valor válido!</span>"
            )
            return

        self.result_label.setStyleSheet(
            "color: #1e3a28; background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #d4edda, stop:1 #c3e6cb); "
            "border-radius: 16px; padding: 20px; border: 3px solid #66bb6a; font-weight: 500;"
        )

        usd = conversion["usd"]
        inputs = conversion["inputs"]
        total = conversion["total"]
        
        result_parts = []
        if inputs["pesos"] > 0:
            result_parts.append(f"<div style='margin: 5px 0;'><b style='font-size: 15px;'>🇨🇴 COP {inputs['pesos']:,.2f}</b> → <b style='color: #2d8659; font-size: 16px;'>${usd['pesos']:.2f} USD</b></div>")
        if inputs["soles"] > 0:
            result_parts.append(f"<div style='margin: 5px 0;'><b style='font-size: 15px;'>🇵🇪 PEN {inputs['soles']:,.2f}</b> → <b style='color: #2d8659; font-size: 16px;'>${usd['soles']:.2f} USD</b></div>")
        if inputs["reais"] > 0:
            result_parts.append(f"<div style='margin: 5px 0;'><b style='font-size: 15px;'>🇧🇷 BRL {inputs['reais']:,.2f}</b> → <b style='color: #2d8659; font-size: 16px;'>${usd['reais']:.2f} USD</b></div>")
        if inputs["btc"] > 0:
            result_parts.append(f"<div style='margin: 5px 0;'><b style='font-size: 15px;'>₿ BTC {inputs['btc']:,.6f}</b> → <b style='color: #2d8659; font-size: 16px;'>${usd['btc']:,.2f} USD</b></div>")
        if inputs["eth"] > 0:
            result_parts.append(f"<div style='margin: 5px 0;'><b style='font-size: 15px;'>⟠ ETH {inputs['eth']:,.4f}</b> → <b style='color: #2d8659; font-size: 16px;'>${usd['eth']:,.2f} USD</b></div>")
        
        result = "".join(result_parts)
        if len(result_parts) > 1:
            result += f"<hr style='border: 2px solid #66bb6a; margin: 12px 0;'><div style='font-size: 19px; margin-top: 8px;'><b>💰 Total: <span style='color: #1e7e34; font-size: 22px;'>${total:,.2f} USD</span></b></div>"
        
        self.result_label.showAnimated(result)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
