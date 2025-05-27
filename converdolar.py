import sys
from PyQt5.QtCore import Qt, QEasingCurve, QPropertyAnimation, QRect, QTimer
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
)
from PyQt5.QtGui import QFont, QColor, QPalette

class AnimatedInput(QFrame):
    def __init__(self, label_text, color, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {color}; border-radius: 15px;")
        self.setMaximumHeight(100)
        layout = QVBoxLayout()
        self.label = QLabel(label_text)
        self.label.setFont(QFont("Arial", 14, QFont.Bold))
        self.label.setStyleSheet("color: #fff;")
        self.input = QLineEdit()
        self.input.setFont(QFont("Arial", 16))
        self.input.setStyleSheet(
            "background: #fff; border: none; border-radius: 10px; padding: 8px 12px;"
        )
        layout.addWidget(self.label)
        layout.addWidget(self.input)
        self.setLayout(layout)

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
    def __init__(self, text, color, parent=None):
        super().__init__(text, parent)
        self.setFont(QFont("Arial", 16, QFont.Bold))
        self.setStyleSheet(
            f"background: {color}; color: #fff; border-radius: 12px; padding: 10px 28px;"
        )

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
        self.setFont(QFont("Arial", 16, QFont.Bold))
        self.setStyleSheet("color: #2c3e50; background: #ecf0f1; border-radius: 10px; padding: 10px;")
        self.setAlignment(Qt.AlignCenter)
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
        self.setWindowTitle("Conversor de Moedas Animado 💸")
        self.setGeometry(100, 100, 470, 520)
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#24243e"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(24)

        self.title = QLabel("💸 Conversor de Moedas Animado")
        self.title.setFont(QFont("Arial", 22, QFont.Bold))
        self.title.setStyleSheet("color: #fff;")
        self.title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)

        self.pesos_input = AnimatedInput("Pesos Colombianos (COP):", "#4e54c8")
        self.soles_input = AnimatedInput("Sol Peruano (PEN):", "#8f94fb")
        self.reais_input = AnimatedInput("Reais (BRL):", "#43cea2")
        layout.addWidget(self.pesos_input)
        layout.addWidget(self.soles_input)
        layout.addWidget(self.reais_input)

        self.button = AnimatedButton("Converter para Dólar", "#ff512f")
        self.button.clicked.connect(self.convert)
        layout.addWidget(self.button)

        self.result_label = ResultLabel()
        layout.addWidget(self.result_label)
        self.setLayout(layout)

        # Animate elements on start (like GSAP stagger)
        QTimer.singleShot(100, self.animStart)

    def animStart(self):
        self.title.setWindowOpacity(0)
        anim = QPropertyAnimation(self.title, b"windowOpacity")
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setDuration(700)
        anim.start()
        self.pesos_input.animateIn(0)
        self.soles_input.animateIn(200)
        self.reais_input.animateIn(400)
        self.button.animateIn(600)

    def convert(self):
        try:
            pesos = float(self.pesos_input.input.text().replace(',', '.')) if self.pesos_input.input.text() else 0
        except Exception:
            pesos = 0
        try:
            soles = float(self.soles_input.input.text().replace(',', '.')) if self.soles_input.input.text() else 0
        except Exception:
            soles = 0
        try:
            reais = float(self.reais_input.input.text().replace(',', '.')) if self.reais_input.input.text() else 0
        except Exception:
            reais = 0

        psdolar = pesos * 0.00024
        soldolar = soles * 0.27
        realdolar = reais * 0.18
        result = (
            f"Pesos Colombianos em Dólar: <b>${psdolar:.2f}</b><br>"
            f"Sol Peruano em Dólar: <b>${soldolar:.2f}</b><br>"
            f"Reais em Dólar: <b>${realdolar:.2f}</b>"
        )
        self.result_label.showAnimated(result)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())