import sys
import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from converdolar import (
    MainWindow, AnimatedInput, AnimatedButton, ResultLabel, convert_amounts,
    COP_TO_USD, PEN_TO_USD, BRL_TO_USD, BTC_TO_USD, ETH_TO_USD,
    GRADIENT_GREEN, GRADIENT_GREEN_HOVER,
)

# Shared QApplication for all tests
app = QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def window():
    """Create a fresh MainWindow for each test."""
    w = MainWindow()
    return w


# ---------- Page / Widget rendering tests ----------

class TestPageRendering:
    def test_window_title(self, window):
        assert "Conversor de Moedas" in window.windowTitle()

    def test_window_minimum_size(self, window):
        assert window.minimumWidth() >= 500
        assert window.minimumHeight() >= 850

    def test_all_currency_inputs_exist(self, window):
        assert window.pesos_input is not None
        assert window.soles_input is not None
        assert window.reais_input is not None

    def test_crypto_inputs_exist(self, window):
        assert window.btc_input is not None
        assert window.eth_input is not None

    def test_buttons_exist(self, window):
        assert window.button is not None
        assert window.clear_button is not None

    def test_result_label_hidden_initially(self, window):
        assert not window.result_label.isVisible()

    def test_title_label_text(self, window):
        assert "Conversor de Moedas" in window.title.text()

    def test_subtitle_label_text(self, window):
        assert "criptomoedas" in window.subtitle.text()

    def test_info_label_shows_rates(self, window):
        info = window.info_label.text()
        assert "BTC" in info
        assert "ETH" in info
        assert "COP" in info


# ---------- Input validation tests ----------

class TestInputValidation:
    def test_parse_valid_float(self, window):
        assert window._parse_currency_input("100.5") == 100.5

    def test_parse_comma_as_decimal(self, window):
        assert window._parse_currency_input("100,5") == 100.5

    def test_parse_empty_string(self, window):
        assert window._parse_currency_input("") == 0.0

    def test_parse_none(self, window):
        assert window._parse_currency_input(None) == 0.0

    def test_parse_invalid_text(self, window):
        assert window._parse_currency_input("abc") == 0.0

    def test_parse_whitespace(self, window):
        assert window._parse_currency_input("   ") == 0.0

    def test_parse_zero(self, window):
        assert window._parse_currency_input("0") == 0.0


# ---------- Button functionality tests ----------

class TestButtons:
    def test_convert_button_text(self, window):
        assert "Converter" in window.button.text()

    def test_clear_button_text(self, window):
        assert "Limpar" in window.clear_button.text()

    def test_convert_button_triggers_convert(self, window):
        window.pesos_input.input.setText("1000")
        window.convert()
        assert window.result_label.text() != ""

    def test_clear_button_clears_all(self, window):
        window.pesos_input.input.setText("1000")
        window.soles_input.input.setText("50")
        window.reais_input.input.setText("200")
        window.btc_input.input.setText("0.1")
        window.eth_input.input.setText("1")
        window.clear_fields()
        assert window.pesos_input.input.text() == ""
        assert window.soles_input.input.text() == ""
        assert window.reais_input.input.text() == ""
        assert window.btc_input.input.text() == ""
        assert window.eth_input.input.text() == ""

    def test_clear_hides_result(self, window):
        window.pesos_input.input.setText("1000")
        window.convert()
        assert window.result_label.text() != ""
        window.clear_fields()
        assert not window.result_label.isVisible()


# ---------- Currency conversion logic tests ----------

class TestCurrencyConversion:
    def test_cop_to_usd(self, window):
        window.pesos_input.input.setText("10000")
        window.convert()
        result = window.result_label.text()
        expected = 10000 * COP_TO_USD
        assert f"${expected:.2f}" in result

    def test_pen_to_usd(self, window):
        window.soles_input.input.setText("100")
        window.convert()
        result = window.result_label.text()
        expected = 100 * PEN_TO_USD
        assert f"${expected:.2f}" in result

    def test_brl_to_usd(self, window):
        window.reais_input.input.setText("50")
        window.convert()
        result = window.result_label.text()
        expected = 50 * BRL_TO_USD
        assert f"${expected:.2f}" in result

    def test_empty_input_shows_error(self, window):
        window.convert()
        result = window.result_label.text()
        assert "válido" in result

    def test_negative_input_shows_error(self, window):
        window.pesos_input.input.setText("-100")
        window.convert()
        result = window.result_label.text()
        assert "inválidos" in result

    def test_multiple_currencies_show_total(self, window):
        window.pesos_input.input.setText("10000")
        window.soles_input.input.setText("100")
        window.convert()
        result = window.result_label.text()
        assert "Total" in result

    def test_single_currency_no_total(self, window):
        window.pesos_input.input.setText("10000")
        window.convert()
        result = window.result_label.text()
        assert "Total" not in result


# ---------- Cryptocurrency conversion tests ----------

class TestCryptoConversion:
    def test_btc_to_usd(self, window):
        window.btc_input.input.setText("0.5")
        window.convert()
        result = window.result_label.text()
        expected = 0.5 * BTC_TO_USD
        assert f"${expected:,.2f}" in result
        assert "BTC" in result

    def test_eth_to_usd(self, window):
        window.eth_input.input.setText("2")
        window.convert()
        result = window.result_label.text()
        expected = 2 * ETH_TO_USD
        assert f"${expected:,.2f}" in result
        assert "ETH" in result

    def test_crypto_and_fiat_together(self, window):
        window.btc_input.input.setText("1")
        window.reais_input.input.setText("100")
        window.convert()
        result = window.result_label.text()
        assert "BTC" in result
        assert "BRL" in result
        assert "Total" in result

    def test_btc_small_amount(self, window):
        window.btc_input.input.setText("0.001")
        window.convert()
        result = window.result_label.text()
        expected = 0.001 * BTC_TO_USD
        assert f"${expected:,.2f}" in result

    def test_eth_large_amount(self, window):
        window.eth_input.input.setText("100")
        window.convert()
        result = window.result_label.text()
        expected = 100 * ETH_TO_USD
        assert f"${expected:,.2f}" in result

    def test_all_five_currencies(self, window):
        window.pesos_input.input.setText("10000")
        window.soles_input.input.setText("100")
        window.reais_input.input.setText("50")
        window.btc_input.input.setText("0.1")
        window.eth_input.input.setText("1")
        window.convert()
        result = window.result_label.text()
        assert "COP" in result
        assert "PEN" in result
        assert "BRL" in result
        assert "BTC" in result
        assert "ETH" in result
        assert "Total" in result


# ---------- Backend conversion helper tests ----------

class TestBackendConversionHelper:
    def test_convert_amounts_returns_totals(self):
        data = convert_amounts(pesos=10000, soles=50, reais=10, btc=0.5, eth=1.2)
        assert pytest.approx(data["inputs"]["pesos"]) == 10000
        assert pytest.approx(data["inputs"]["soles"]) == 50
        assert pytest.approx(data["inputs"]["reais"]) == 10
        assert pytest.approx(data["inputs"]["btc"]) == 0.5
        assert pytest.approx(data["inputs"]["eth"]) == 1.2
        assert pytest.approx(data["usd"]["pesos"]) == 10000 * COP_TO_USD
        assert pytest.approx(data["usd"]["soles"]) == 50 * PEN_TO_USD
        assert pytest.approx(data["usd"]["reais"]) == 10 * BRL_TO_USD
        assert pytest.approx(data["usd"]["btc"]) == 0.5 * BTC_TO_USD
        assert pytest.approx(data["usd"]["eth"]) == 1.2 * ETH_TO_USD
        assert pytest.approx(data["total"]) == sum(data["usd"].values())

    def test_convert_amounts_rejects_negative(self):
        with pytest.raises(ValueError, match="Valor negativo .*Pesos Colombianos"):
            convert_amounts(pesos=-1)

    def test_convert_amounts_rejects_non_numeric(self):
        with pytest.raises(ValueError, match="Valor inválido 'abc' para Sol Peruano"):
            convert_amounts(soles="abc")

    def test_convert_amounts_handles_zero_values(self):
        data = convert_amounts(pesos=0, soles=0, reais=0, btc=0, eth=0)
        assert data["total"] == 0
        assert all(value == 0 for value in data["usd"].values())


# ---------- Widget component tests ----------

class TestWidgetComponents:
    def test_animated_input_label(self):
        ai = AnimatedInput("Test Label", "#333333", "placeholder")
        assert ai.label.text() == "Test Label"

    def test_animated_input_placeholder(self):
        ai = AnimatedInput("Label", "#333333", "my placeholder")
        assert ai.input.placeholderText() == "my placeholder"

    def test_animated_button_creation(self):
        btn = AnimatedButton("Click Me", GRADIENT_GREEN, GRADIENT_GREEN_HOVER)
        assert btn.text() == "Click Me"

    def test_result_label_hidden_by_default(self):
        rl = ResultLabel()
        assert not rl.isVisible()

    def test_result_label_show_animated(self):
        rl = ResultLabel()
        rl.showAnimated("Test Result")
        assert rl.text() == "Test Result"
        assert rl.isVisible()
