import sys
from PyQt5.QtCore import Qt, QEasingCurve, QPropertyAnimation, QRect, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QComboBox, QScrollArea, QGraphicsOpacityEffect,
)
from PyQt5.QtGui import QFont, QColor, QPalette, QDoubleValidator

from backend import (
    COP_TO_USD,
    PEN_TO_USD,
    BRL_TO_USD,
    BTC_TO_USD,
    ETH_TO_USD,
    USD_TO_COP,
    USD_TO_PEN,
    USD_TO_BRL,
    convert_amounts,
    convert_asset_amount,
    get_market_snapshot,
)

# ─── Gradient / color constants ───────────────────────────────────────────────
GRADIENT_PURPLE_VIOLET = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #667eea, stop:1 #764ba2)"
GRADIENT_PINK_RED = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f093fb, stop:1 #f5576c)"
GRADIENT_CYAN_TURQUOISE = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4facfe, stop:1 #00f2fe)"
GRADIENT_GREEN = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #56ab2f, stop:1 #a8e063)"
GRADIENT_GREEN_HOVER = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a9628, stop:1 #95c956)"
GRADIENT_ORANGE_GOLD = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f7971e, stop:1 #ffd200)"
GRADIENT_INDIGO_BLUE = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #667eea, stop:1 #4facfe)"
GRADIENT_GRAY = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #434343, stop:1 #000000)"
GRADIENT_GRAY_HOVER = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #525252, stop:1 #1a1a1a)"

# Currency display labels
_CURRENCY_DISPLAY = {
    "BRL": "🇧🇷 BRL",
    "COP": "🇨🇴 COP",
    "PEN": "🇵🇪 PEN",
    "USD": "🇺🇸 USD",
    "EUR": "🇪🇺 EUR",
    "BTC": "₿  BTC",
    "ETH": "⟠  ETH",
    "USDT": "🪙 USDT",
}
_DEFAULT_SYMBOLS = ["BRL", "COP", "PEN", "USD", "EUR", "BTC", "ETH", "USDT"]


def _fade_in(widget, duration: int = 400) -> None:
    """Fade a widget in using QGraphicsOpacityEffect (works for any widget)."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity")
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(duration)
    anim.setEasingCurve(QEasingCurve.InOutQuad)
    widget.show()
    anim.start()
    widget._fade_anim = anim  # prevent GC


# ─── Background market-refresh thread ────────────────────────────────────────
class MarketRefreshThread(QThread):
    """Fetches a fresh market snapshot in a background thread."""

    data_ready = pyqtSignal(dict)

    def run(self) -> None:
        try:
            snapshot = get_market_snapshot(allow_network=True)
            self.data_ready.emit(snapshot)
        except Exception:
            pass


# ─── Live / cache / offline status indicator ─────────────────────────────────
class StatusDot(QWidget):
    """Colored dot + text showing whether rates are live, cached, or offline."""

    LIVE = "live"
    CACHE = "cache"
    OFFLINE = "offline"

    def __init__(self, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)
        self.dot = QLabel("●")
        self.dot.setFont(QFont("Segoe UI", 12))
        self.dot.setStyleSheet("background: transparent;")
        self.text = QLabel("Conectando…")
        self.text.setFont(QFont("Segoe UI", 10))
        self.text.setStyleSheet("background: transparent;")
        row.addWidget(self.dot)
        row.addWidget(self.text)
        self.set_state(self.OFFLINE)

    def set_state(self, state: str) -> None:
        _map = {
            self.LIVE: ("#2ecc71", "Ao vivo"),
            self.CACHE: ("#f1c40f", "Cache"),
            self.OFFLINE: ("#e74c3c", "Offline"),
        }
        color, label = _map.get(state, ("#e74c3c", "Offline"))
        style = f"color: {color}; background: transparent;"
        self.dot.setStyleSheet(style)
        self.text.setStyleSheet(style)
        self.text.setText(label)


# ─── Universal converter panel ────────────────────────────────────────────────
class UniversalConverterPanel(QFrame):
    """Convert any supported asset to any other using convert_asset_amount."""

    _COMBO_STYLE = """
        QComboBox {
            background: #1e2940; color: #ffffff;
            border: 2px solid #2a3550; border-radius: 10px;
            padding: 9px 12px; font-size: 13px;
        }
        QComboBox:hover { border-color: #667eea; }
        QComboBox::drop-down { border: none; width: 24px; }
        QComboBox::down-arrow {
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid #8b92a8;
            margin-right: 8px;
        }
        QComboBox QAbstractItemView {
            background: #1e2940; color: #ffffff;
            selection-background-color: #3a4560;
            border: 1px solid #3a4560; outline: none;
        }
    """
    _SMALL_INPUT_STYLE = """
        QLineEdit {
            background: #0f1419; border: 1px solid #2a3550;
            border-radius: 7px; padding: 6px 10px; color: #ffffff;
        }
        QLineEdit:focus { border-color: #667eea; }
    """

    def __init__(self, rates_to_usd: dict, parent=None):
        super().__init__(parent)
        self._rates = rates_to_usd
        self._current_result_text = ""
        self._setup_ui()

    # ── construction ─────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setObjectName("universalPanel")
        self.setStyleSheet(
            "QFrame#universalPanel {"
            "  background: #161d2e; border-radius: 20px; border: 1px solid #2a3550;"
            "}"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 22)
        outer.setSpacing(12)

        # Header
        hdr = QLabel("🔄 Conversor Universal")
        hdr.setFont(QFont("Segoe UI", 14, QFont.Bold))
        hdr.setStyleSheet("color: #ffffff; background: transparent; border: none;")
        outer.addWidget(hdr)

        sub = QLabel("Converta entre qualquer par de moedas ou criptoativos")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet("color: #8b92a8; background: transparent; border: none;")
        outer.addWidget(sub)

        # From row
        from_row = QHBoxLayout()
        from_row.setSpacing(10)
        lbl_from = self._row_label("De")
        self.from_combo = self._make_combo()
        self.amount_input = QLineEdit()
        self.amount_input.setFont(QFont("Segoe UI", 14))
        self.amount_input.setPlaceholderText("Valor")
        self.amount_input.setClearButtonEnabled(True)
        _v = QDoubleValidator(0.0, 1e12, 8)
        _v.setNotation(QDoubleValidator.StandardNotation)
        self.amount_input.setValidator(_v)
        self.amount_input.setStyleSheet(
            "QLineEdit { background: #1e2940; border: 2px solid #2a3550;"
            " border-radius: 10px; padding: 9px 14px; color: #ffffff; font-size: 14px; }"
            "QLineEdit:focus { border-color: #667eea; }"
        )
        self.amount_input.returnPressed.connect(self.do_convert)
        from_row.addWidget(lbl_from)
        from_row.addWidget(self.from_combo, 3)
        from_row.addWidget(self.amount_input, 2)
        outer.addLayout(from_row)

        # Swap button
        swap_row = QHBoxLayout()
        swap_row.addStretch()
        self.swap_btn = QPushButton("↕ Trocar")
        self.swap_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.swap_btn.setCursor(Qt.PointingHandCursor)
        self.swap_btn.setFixedSize(96, 30)
        self.swap_btn.setStyleSheet(
            "QPushButton { background: #2a3550; color: #8b92a8;"
            " border-radius: 8px; border: 1px solid #3a4560; }"
            "QPushButton:hover { background: #3a4560; color: #ffffff; }"
        )
        self.swap_btn.clicked.connect(self.swap_currencies)
        swap_row.addWidget(self.swap_btn)
        swap_row.addStretch()
        outer.addLayout(swap_row)

        # To row
        to_row = QHBoxLayout()
        to_row.setSpacing(10)
        lbl_to = self._row_label("Para")
        self.to_combo = self._make_combo()
        to_row.addWidget(lbl_to)
        to_row.addWidget(self.to_combo, 3)
        to_row.addStretch(2)
        outer.addLayout(to_row)

        # Settings toggle
        self.settings_btn = QPushButton("⚙  Taxa / Spread ▾")
        self.settings_btn.setFont(QFont("Segoe UI", 10))
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setCheckable(True)
        self.settings_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #667eea;"
            " border: none; text-align: left; padding: 0; }"
            "QPushButton:hover { color: #8b92a8; }"
        )
        self.settings_btn.toggled.connect(self._toggle_settings)
        outer.addWidget(self.settings_btn)

        # Settings frame (hidden by default)
        self.settings_frame = QFrame()
        self.settings_frame.setStyleSheet(
            "QFrame { background: #1e2940; border-radius: 10px; border: 1px solid #2a3550; }"
        )
        sf = QHBoxLayout(self.settings_frame)
        sf.setContentsMargins(14, 10, 14, 10)
        sf.setSpacing(20)
        for attr, lbl_txt in (("fee_input", "Taxa (%)"), ("spread_input", "Spread (%)")):
            col = QVBoxLayout()
            col.setSpacing(4)
            l = QLabel(lbl_txt)
            l.setFont(QFont("Segoe UI", 9))
            l.setStyleSheet("color: #8b92a8; background: transparent; border: none;")
            inp = QLineEdit("0")
            inp.setFont(QFont("Segoe UI", 12))
            inp.setFixedWidth(80)
            inp.setStyleSheet(self._SMALL_INPUT_STYLE)
            pv = QDoubleValidator(0.0, 99.99, 4)
            pv.setNotation(QDoubleValidator.StandardNotation)
            inp.setValidator(pv)
            setattr(self, attr, inp)
            col.addWidget(l)
            col.addWidget(inp)
            sf.addLayout(col)
        sf.addStretch()
        self.settings_frame.hide()
        outer.addWidget(self.settings_frame)

        # Convert button
        self.convert_btn = QPushButton("💱 Converter")
        self.convert_btn.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.convert_btn.setCursor(Qt.PointingHandCursor)
        self.convert_btn.setMinimumHeight(50)
        self.convert_btn.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #11998e,stop:1 #38ef7d); color:#fff; border-radius:13px; border:none; font-weight:700; }"
            "QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #0e8a7e,stop:1 #2fd970); }"
            "QPushButton:pressed { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #0b7a6e,stop:1 #28c262); }"
        )
        self.convert_btn.clicked.connect(self.do_convert)
        outer.addWidget(self.convert_btn)

        # Result main label
        self.result_main = QLabel()
        self.result_main.setFont(QFont("Segoe UI", 17, QFont.Bold))
        self.result_main.setWordWrap(True)
        self.result_main.setAlignment(Qt.AlignCenter)
        self.result_main.setMinimumHeight(60)
        self._set_result_style_ok()
        self.result_main.hide()
        outer.addWidget(self.result_main)

        # Breakdown label (fee / spread detail)
        self.result_breakdown = QLabel()
        self.result_breakdown.setFont(QFont("Segoe UI", 10))
        self.result_breakdown.setWordWrap(True)
        self.result_breakdown.setAlignment(Qt.AlignCenter)
        self.result_breakdown.setStyleSheet(
            "background: #1e2940; border: 1px solid #2a3550;"
            " border-radius: 10px; padding: 8px 14px; color: #8b92a8;"
        )
        self.result_breakdown.hide()
        outer.addWidget(self.result_breakdown)

        # Copy button
        copy_row = QHBoxLayout()
        copy_row.addStretch()
        self.copy_btn = QPushButton("📋 Copiar")
        self.copy_btn.setFont(QFont("Segoe UI", 10))
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setFixedSize(90, 28)
        self.copy_btn.setStyleSheet(
            "QPushButton { background: #2a3550; color: #8b92a8;"
            " border-radius: 6px; border: 1px solid #3a4560; }"
            "QPushButton:hover { background: #3a4560; color: #ffffff; }"
        )
        self.copy_btn.clicked.connect(self._copy_result)
        self.copy_btn.hide()
        copy_row.addWidget(self.copy_btn)
        outer.addLayout(copy_row)

        self._populate_combos(_DEFAULT_SYMBOLS)

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _row_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl.setStyleSheet("color: #8b92a8; background: transparent; border: none;")
        lbl.setFixedWidth(40)
        return lbl

    def _make_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setFont(QFont("Segoe UI", 12))
        combo.setCursor(Qt.PointingHandCursor)
        combo.setStyleSheet(self._COMBO_STYLE)
        return combo

    def _populate_combos(self, symbols: list) -> None:
        prev_from = self.from_combo.currentData()
        prev_to = self.to_combo.currentData()
        for combo in (self.from_combo, self.to_combo):
            combo.blockSignals(True)
            combo.clear()
            for sym in symbols:
                combo.addItem(_CURRENCY_DISPLAY.get(sym, sym), sym)
            combo.blockSignals(False)

        def _restore(combo, prev, fallback):
            idx = combo.findData(prev) if prev else -1
            if idx < 0:
                idx = combo.findData(fallback)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        _restore(self.from_combo, prev_from, "BRL")
        _restore(self.to_combo, prev_to, "USD")

    def _set_result_style_ok(self) -> None:
        self.result_main.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #0d2137,stop:1 #0a1a2e);"
            "border: 2px solid #11998e; border-radius: 14px;"
            "padding: 14px; color: #38ef7d;"
        )

    @staticmethod
    def _parse(text: str, default: float = 0.0) -> float:
        try:
            return float(str(text).replace(",", "."))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _fmt(val: float, sym: str) -> str:
        if sym in ("BTC", "ETH"):
            return f"{val:,.6f}"
        return f"{val:,.2f}"

    # ── public interface ──────────────────────────────────────────────────────

    def update_rates(self, rates_to_usd: dict) -> None:
        self._rates = rates_to_usd

    def update_symbols(self, symbols: list) -> None:
        if symbols:
            self._populate_combos(symbols)

    def swap_currencies(self) -> None:
        fi, ti = self.from_combo.currentIndex(), self.to_combo.currentIndex()
        self.from_combo.setCurrentIndex(ti)
        self.to_combo.setCurrentIndex(fi)

    def _toggle_settings(self, checked: bool) -> None:
        self.settings_frame.setVisible(checked)
        arrow = "▴" if checked else "▾"
        self.settings_btn.setText(f"⚙  Taxa / Spread {arrow}")

    def do_convert(self) -> None:
        amount = self._parse(self.amount_input.text())
        if amount <= 0:
            self._show_error("⚠️ Digite um valor maior que zero.")
            return

        from_sym = self.from_combo.currentData()
        to_sym = self.to_combo.currentData()
        fee = self._parse(self.fee_input.text())
        spread = self._parse(self.spread_input.text())

        try:
            res = convert_asset_amount(
                amount=amount,
                from_symbol=from_sym,
                to_symbol=to_sym,
                fee_percent=fee,
                spread_percent=spread,
                rates_to_usd=self._rates,
                allow_network=False,
            )
        except ValueError as exc:
            self._show_error(f"⚠️ {exc}")
            return

        net = res["result"]["net"]
        gross = res["result"]["gross"]
        fee_amt = res["result"]["fee_amount"]
        spread_amt = res["result"]["spread_amount"]

        main_txt = (
            f"{self._fmt(amount, from_sym)} {from_sym}"
            "  =  "
            f"{self._fmt(net, to_sym)} {to_sym}"
        )
        self._current_result_text = main_txt
        self._set_result_style_ok()
        self.result_main.setText(main_txt)
        _fade_in(self.result_main)

        if fee > 0 or spread > 0:
            bd = (
                f"Bruto: {self._fmt(gross, to_sym)}  |  "
                f"Spread: {self._fmt(spread_amt, to_sym)}  |  "
                f"Taxa: {self._fmt(fee_amt, to_sym)}"
            )
            self.result_breakdown.setText(bd)
            _fade_in(self.result_breakdown)
        else:
            self.result_breakdown.hide()

        _fade_in(self.copy_btn)

    def _show_error(self, msg: str) -> None:
        self.result_main.setText(msg)
        self.result_main.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #2d0a0a,stop:1 #1a0808);"
            "border: 2px solid #e74c3c; border-radius: 14px;"
            "padding: 14px; color: #e74c3c;"
        )
        _fade_in(self.result_main)
        self.result_breakdown.hide()
        self.copy_btn.hide()

    def _copy_result(self) -> None:
        if self._current_result_text:
            QApplication.clipboard().setText(self._current_result_text)
            self.copy_btn.setText("✓ Copiado!")
            QTimer.singleShot(2000, lambda: self.copy_btn.setText("📋 Copiar"))


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
        _fade_in(self, duration=500)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("💸 Conversor de Moedas")
        self.setGeometry(100, 100, 560, 980)
        self.setMinimumSize(500, 850)

        self.current_rates_to_usd = {
            "COP": COP_TO_USD,
            "PEN": PEN_TO_USD,
            "BRL": BRL_TO_USD,
            "BTC": BTC_TO_USD,
            "ETH": ETH_TO_USD,
            "USD": 1.0,
            "USDT": 1.0,
            "EUR": 1.08,
        }
        self.last_market_timestamp = None

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#0f1419"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # Scroll area wraps all content so the window is never clipped
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { background: #0f1419; width: 8px; border-radius: 4px; }"
            "QScrollBar::handle:vertical { background: #2a3550; border-radius: 4px; min-height: 20px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(18)

        # ── Header ────────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(6)

        self.title = QLabel("💸 Conversor de Moedas")
        self.title.setFont(QFont("Segoe UI", 26, QFont.Bold))
        self.title.setStyleSheet("color: #ffffff;")
        self.title.setAlignment(Qt.AlignLeft)

        self.subtitle = QLabel("Converta moedas e criptomoedas para qualquer ativo")
        self.subtitle.setFont(QFont("Segoe UI", 12))
        self.subtitle.setStyleSheet("color: #8b92a8;")
        self.subtitle.setAlignment(Qt.AlignLeft)

        title_col.addWidget(self.title)
        title_col.addWidget(self.subtitle)

        self.status_dot = StatusDot()
        header_row.addLayout(title_col)
        header_row.addStretch()
        header_row.addWidget(self.status_dot, alignment=Qt.AlignBottom)
        layout.addLayout(header_row)

        # ── Universal converter ───────────────────────────────────────────────
        self.universal_panel = UniversalConverterPanel(dict(self.current_rates_to_usd))
        layout.addWidget(self.universal_panel)

        # ── Section divider ───────────────────────────────────────────────────
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setMaximumHeight(1)
        div.setStyleSheet("background: #2a3550; border: none;")
        layout.addWidget(div)

        multi_lbl = QLabel("📊 Conversão múltipla → USD")
        multi_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        multi_lbl.setStyleSheet("color: #8b92a8;")
        layout.addWidget(multi_lbl)

        # ── Multi-currency inputs ─────────────────────────────────────────────
        self.pesos_input = AnimatedInput("🇨🇴 Pesos Colombianos (COP)", GRADIENT_PURPLE_VIOLET, "Ex: 10000")
        self.soles_input = AnimatedInput("🇵🇪 Sol Peruano (PEN)", GRADIENT_PINK_RED, "Ex: 100")
        self.reais_input = AnimatedInput("🇧🇷 Real Brasileiro (BRL)", GRADIENT_CYAN_TURQUOISE, "Ex: 50")
        self.btc_input = AnimatedInput("₿ Bitcoin (BTC)", GRADIENT_ORANGE_GOLD, "Ex: 0.5")
        self.eth_input = AnimatedInput("⟠ Ethereum (ETH)", GRADIENT_INDIGO_BLUE, "Ex: 2.0")

        for inp in (self.pesos_input, self.soles_input, self.reais_input, self.btc_input, self.eth_input):
            layout.addWidget(inp)

        # ── Action buttons ────────────────────────────────────────────────────
        button_layout = QVBoxLayout()
        button_layout.setSpacing(14)

        self.button = AnimatedButton("💱 Converter para Dólar (USD)", GRADIENT_GREEN, GRADIENT_GREEN_HOVER)
        self.button.clicked.connect(self.convert)
        button_layout.addWidget(self.button)

        self.clear_button = AnimatedButton("🔄 Limpar Todos os Campos", GRADIENT_GRAY, GRADIENT_GRAY_HOVER)
        self.clear_button.clicked.connect(self.clear_fields)
        button_layout.addWidget(self.clear_button)

        layout.addLayout(button_layout)

        # ── Hint ──────────────────────────────────────────────────────────────
        self.hint_label = QLabel("💡 Dica: pressione Enter em qualquer campo para converter rapidamente.")
        self.hint_label.setFont(QFont("Segoe UI", 10))
        self.hint_label.setStyleSheet("color: #9aa5b1; padding: 6px 8px;")
        self.hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.hint_label)

        # ── Rates info bar ────────────────────────────────────────────────────
        self.info_label = QLabel(self._build_market_info_text())
        self.info_label.setFont(QFont("Segoe UI", 10))
        self.info_label.setStyleSheet(
            "color: #6c7a89; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 8px;"
        )
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)

        # ── Multi-currency result ─────────────────────────────────────────────
        self.result_label = ResultLabel()
        layout.addWidget(self.result_label)

        layout.addStretch()

        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

        # Enter key on every currency input triggers multi-currency convert
        for inp in (
            self.pesos_input.input, self.soles_input.input, self.reais_input.input,
            self.btc_input.input, self.eth_input.input,
        ):
            inp.returnPressed.connect(self.convert)

        # Startup: static data first, then async live fetch
        QTimer.singleShot(100, self.animStart)
        self.refresh_market_info(allow_network=False)
        QTimer.singleShot(300, self._start_live_refresh)

        self.market_timer = QTimer(self)
        self.market_timer.setInterval(20000)
        self.market_timer.timeout.connect(self._start_live_refresh)
        self.market_timer.start()

    # ── market data ───────────────────────────────────────────────────────────

    def _build_market_info_text(self) -> str:
        ts = self.last_market_timestamp or "sem atualização online"
        r = self.current_rates_to_usd
        return (
            f"📊 1 USD = {1.0 / r.get('COP', COP_TO_USD):.2f} COP | "
            f"{1.0 / r.get('PEN', PEN_TO_USD):.2f} PEN | "
            f"{1.0 / r.get('BRL', BRL_TO_USD):.2f} BRL\n"
            f"₿ 1 BTC = ${r.get('BTC', BTC_TO_USD):,.2f} | "
            f"⟠ 1 ETH = ${r.get('ETH', ETH_TO_USD):,.2f} | "
            f"🕒 Atualizado: {ts}"
        )

    def refresh_market_info(self, allow_network: bool = True) -> None:
        """Synchronous refresh — use only with allow_network=False on startup."""
        try:
            snapshot = get_market_snapshot(allow_network=allow_network)
            rates = snapshot.get("rates_to_usd", {})
            for sym in ("COP", "PEN", "BRL", "BTC", "ETH", "USD", "USDT", "EUR"):
                raw = rates.get(sym)
                if isinstance(raw, (int, float)) and raw > 0:
                    self.current_rates_to_usd[sym] = float(raw)
            self.last_market_timestamp = str(
                snapshot.get("updated_at") or self.last_market_timestamp or "N/A"
            )
        except Exception:
            pass
        self.info_label.setText(self._build_market_info_text())

    def _start_live_refresh(self) -> None:
        """Launch a background thread to fetch live rates without blocking the UI."""
        if hasattr(self, "_refresh_thread") and self._refresh_thread.isRunning():
            return
        self.status_dot.set_state(StatusDot.CACHE)
        self._refresh_thread = MarketRefreshThread()
        self._refresh_thread.data_ready.connect(self._on_market_data)
        self._refresh_thread.start()

    def _on_market_data(self, snapshot: dict) -> None:
        """Handle fresh market data received from the background thread."""
        rates = snapshot.get("rates_to_usd", {})
        for sym in ("COP", "PEN", "BRL", "BTC", "ETH", "USD", "USDT", "EUR"):
            raw = rates.get(sym)
            if isinstance(raw, (int, float)) and raw > 0:
                self.current_rates_to_usd[sym] = float(raw)
        self.last_market_timestamp = str(snapshot.get("updated_at") or "N/A")

        sources = snapshot.get("sources", {})
        if "static-fallback" in str(sources.get("crypto", "")):
            self.status_dot.set_state(StatusDot.OFFLINE)
        else:
            self.status_dot.set_state(StatusDot.LIVE)

        self.info_label.setText(self._build_market_info_text())
        self.universal_panel.update_rates(dict(self.current_rates_to_usd))
        symbols = list(snapshot.get("symbols", []))
        if symbols:
            self.universal_panel.update_symbols(symbols)

    # ── UI actions ────────────────────────────────────────────────────────────

    def clear_fields(self) -> None:
        for inp in (
            self.pesos_input.input, self.soles_input.input, self.reais_input.input,
            self.btc_input.input, self.eth_input.input,
        ):
            inp.clear()
        self.result_label.hide()
        self.pesos_input.input.setFocus()

    def animStart(self) -> None:
        _fade_in(self.title, duration=700)
        _fade_in(self.subtitle, duration=700)
        self.pesos_input.animateIn(0)
        self.soles_input.animateIn(200)
        self.reais_input.animateIn(400)
        self.btc_input.animateIn(500)
        self.eth_input.animateIn(600)
        self.button.animateIn(700)
        self.clear_button.animateIn(800)

    def _parse_currency_input(self, input_text) -> float:
        try:
            if input_text and str(input_text).strip():
                return float(str(input_text).replace(",", "."))
        except (ValueError, AttributeError):
            pass
        return 0.0

    def convert(self) -> None:
        pesos = self._parse_currency_input(self.pesos_input.input.text())
        soles = self._parse_currency_input(self.soles_input.input.text())
        reais = self._parse_currency_input(self.reais_input.input.text())
        btc = self._parse_currency_input(self.btc_input.input.text())
        eth = self._parse_currency_input(self.eth_input.input.text())

        try:
            conversion = convert_amounts(
                pesos, soles, reais, btc, eth,
                rates_to_usd=self.current_rates_to_usd,
            )
        except ValueError:
            self.result_label.setStyleSheet(
                "color: #721c24; background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
                " stop:0 #f8d7da, stop:1 #f5c6cb);"
                " border-radius: 16px; padding: 20px; border: 3px solid #f44336; font-weight: 500;"
            )
            self.result_label.showAnimated(
                "<span style='color:#c0392b; font-weight:bold; font-size:15px;'>"
                "⚠️ Valores inválidos. Por favor, insira apenas números positivos.</span>"
            )
            return

        has_valid_input = any(v > 0 for v in conversion["inputs"].values())
        if not has_valid_input:
            self.result_label.setStyleSheet(
                "color: #721c24; background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
                " stop:0 #f8d7da, stop:1 #f5c6cb);"
                " border-radius: 16px; padding: 20px; border: 3px solid #f44336; font-weight: 500;"
            )
            self.result_label.showAnimated(
                "<span style='color:#c0392b; font-weight:bold; font-size:15px;'>"
                "⚠️ Por favor, insira pelo menos um valor válido!</span>"
            )
            return

        self.result_label.setStyleSheet(
            "color: #1e3a28; background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            " stop:0 #d4edda, stop:1 #c3e6cb);"
            " border-radius: 16px; padding: 20px; border: 3px solid #66bb6a; font-weight: 500;"
        )

        usd = conversion["usd"]
        inputs = conversion["inputs"]
        total = conversion["total"]

        parts = []
        if inputs["pesos"] > 0:
            parts.append(
                f"<div style='margin:5px 0;'><b style='font-size:15px;'>🇨🇴 COP {inputs['pesos']:,.2f}</b>"
                f" → <b style='color:#2d8659; font-size:16px;'>${usd['pesos']:.2f} USD</b></div>"
            )
        if inputs["soles"] > 0:
            parts.append(
                f"<div style='margin:5px 0;'><b style='font-size:15px;'>🇵🇪 PEN {inputs['soles']:,.2f}</b>"
                f" → <b style='color:#2d8659; font-size:16px;'>${usd['soles']:.2f} USD</b></div>"
            )
        if inputs["reais"] > 0:
            parts.append(
                f"<div style='margin:5px 0;'><b style='font-size:15px;'>🇧🇷 BRL {inputs['reais']:,.2f}</b>"
                f" → <b style='color:#2d8659; font-size:16px;'>${usd['reais']:.2f} USD</b></div>"
            )
        if inputs["btc"] > 0:
            parts.append(
                f"<div style='margin:5px 0;'><b style='font-size:15px;'>₿ BTC {inputs['btc']:,.6f}</b>"
                f" → <b style='color:#2d8659; font-size:16px;'>${usd['btc']:,.2f} USD</b></div>"
            )
        if inputs["eth"] > 0:
            parts.append(
                f"<div style='margin:5px 0;'><b style='font-size:15px;'>⟠ ETH {inputs['eth']:,.4f}</b>"
                f" → <b style='color:#2d8659; font-size:16px;'>${usd['eth']:,.2f} USD</b></div>"
            )

        result = "".join(parts)
        if len(parts) > 1:
            result += (
                "<hr style='border:2px solid #66bb6a; margin:12px 0;'>"
                f"<div style='font-size:19px; margin-top:8px;'><b>💰 Total: "
                f"<span style='color:#1e7e34; font-size:22px;'>${total:,.2f} USD</span></b></div>"
            )

        self.result_label.showAnimated(result)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
