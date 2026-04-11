import sys
import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication

from converdolar import (
    MainWindow, AnimatedInput, AnimatedButton, ResultLabel, convert_amounts,
    UniversalConverterPanel, StatusDot,
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
        with pytest.raises(ValueError, match="Valor inválido 'abc' para Soles Peruanos"):
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


# ---------- StatusDot widget tests ----------

class TestStatusDot:
    def test_initial_state_is_offline(self):
        dot = StatusDot()
        assert "Offline" in dot.text.text()

    def test_set_state_live(self):
        dot = StatusDot()
        dot.set_state(StatusDot.LIVE)
        assert "vivo" in dot.text.text() or "Ao vivo" in dot.text.text()

    def test_set_state_cache(self):
        dot = StatusDot()
        dot.set_state(StatusDot.CACHE)
        assert "Cache" in dot.text.text()

    def test_set_state_offline(self):
        dot = StatusDot()
        dot.set_state(StatusDot.LIVE)
        dot.set_state(StatusDot.OFFLINE)
        assert "Offline" in dot.text.text()

    def test_set_unknown_state_defaults_to_offline_style(self):
        dot = StatusDot()
        dot.set_state("unknown_state")
        assert "Offline" in dot.text.text()


# ---------- UniversalConverterPanel tests ----------

_DEFAULT_RATES = {
    "BRL": BRL_TO_USD,
    "COP": COP_TO_USD,
    "PEN": PEN_TO_USD,
    "USD": 1.0,
    "EUR": 1.08,
    "BTC": BTC_TO_USD,
    "ETH": ETH_TO_USD,
    "USDT": 1.0,
}


@pytest.fixture
def panel():
    return UniversalConverterPanel(dict(_DEFAULT_RATES))


class TestUniversalConverterPanel:
    def test_panel_has_from_combo(self, panel):
        assert panel.from_combo is not None

    def test_panel_has_to_combo(self, panel):
        assert panel.to_combo is not None

    def test_panel_has_amount_input(self, panel):
        assert panel.amount_input is not None

    def test_panel_has_convert_button(self, panel):
        assert panel.convert_btn is not None

    def test_panel_has_swap_button(self, panel):
        assert panel.swap_btn is not None

    def test_panel_combos_populated(self, panel):
        assert panel.from_combo.count() > 0
        assert panel.to_combo.count() > 0

    def test_panel_default_from_currency(self, panel):
        assert panel.from_combo.currentData() == "BRL"

    def test_panel_default_to_currency(self, panel):
        assert panel.to_combo.currentData() == "USD"

    def test_do_convert_zero_amount_shows_error(self, panel):
        panel.amount_input.setText("0")
        panel.do_convert()
        assert "zero" in panel.result_main.text().lower() or ">" in panel.result_main.text()
        assert not panel.result_main.isHidden()

    def test_do_convert_empty_amount_shows_error(self, panel):
        panel.amount_input.setText("")
        panel.do_convert()
        assert not panel.result_main.isHidden()

    def test_do_convert_valid_amount_shows_result(self, panel):
        panel.amount_input.setText("1000")
        panel.from_combo.setCurrentIndex(panel.from_combo.findData("BRL"))
        panel.to_combo.setCurrentIndex(panel.to_combo.findData("USD"))
        panel.do_convert()
        text = panel.result_main.text()
        assert "BRL" in text
        assert "USD" in text
        assert not panel.result_main.isHidden()

    def test_do_convert_shows_copy_button_after_success(self, panel):
        panel.amount_input.setText("500")
        panel.from_combo.setCurrentIndex(panel.from_combo.findData("BRL"))
        panel.to_combo.setCurrentIndex(panel.to_combo.findData("USD"))
        panel.do_convert()
        assert not panel.copy_btn.isHidden()

    def test_do_convert_with_fee_shows_breakdown(self, panel):
        panel.amount_input.setText("1000")
        panel.fee_input.setText("1")
        panel.spread_input.setText("0.5")
        panel.from_combo.setCurrentIndex(panel.from_combo.findData("BRL"))
        panel.to_combo.setCurrentIndex(panel.to_combo.findData("USD"))
        panel.do_convert()
        assert not panel.result_breakdown.isHidden()
        assert "Bruto" in panel.result_breakdown.text()

    def test_do_convert_without_fee_hides_breakdown(self, panel):
        panel.amount_input.setText("1000")
        panel.fee_input.setText("0")
        panel.spread_input.setText("0")
        panel.from_combo.setCurrentIndex(panel.from_combo.findData("BRL"))
        panel.to_combo.setCurrentIndex(panel.to_combo.findData("USD"))
        panel.do_convert()
        assert not panel.result_breakdown.isVisible()

    def test_swap_currencies_exchanges_combos(self, panel):
        panel.from_combo.setCurrentIndex(panel.from_combo.findData("BRL"))
        panel.to_combo.setCurrentIndex(panel.to_combo.findData("USD"))
        panel.swap_currencies()
        assert panel.from_combo.currentData() == "USD"
        assert panel.to_combo.currentData() == "BRL"

    def test_toggle_settings_shows_frame(self, panel):
        assert panel.settings_frame.isHidden()
        panel._toggle_settings(True)
        assert not panel.settings_frame.isHidden()

    def test_toggle_settings_hides_frame(self, panel):
        panel._toggle_settings(True)
        panel._toggle_settings(False)
        assert panel.settings_frame.isHidden()

    def test_update_rates_changes_internal_rates(self, panel):
        new_rates = dict(_DEFAULT_RATES)
        new_rates["BTC"] = 99999.0
        panel.update_rates(new_rates)
        assert panel._rates["BTC"] == 99999.0

    def test_update_symbols_repopulates_combos(self, panel):
        panel.update_symbols(["USD", "EUR"])
        symbols = [panel.from_combo.itemData(i) for i in range(panel.from_combo.count())]
        assert "USD" in symbols
        assert "EUR" in symbols

    def test_update_symbols_empty_list_does_not_repopulate(self, panel):
        original_count = panel.from_combo.count()
        panel.update_symbols([])
        assert panel.from_combo.count() == original_count

    def test_copy_button_hidden_initially(self, panel):
        assert not panel.copy_btn.isVisible()

    def test_result_breakdown_hidden_initially(self, panel):
        assert not panel.result_breakdown.isVisible()

    def test_result_main_hidden_initially(self, panel):
        assert not panel.result_main.isVisible()


# ---------- AnimatedInput validation tests ----------

class TestAnimatedInputValidation:
    def test_validate_valid_number_sets_green_border(self):
        ai = AnimatedInput("Label", "#333333", "placeholder")
        ai.input.setText("123.45")
        ai.validateInput()
        style = ai.input.styleSheet()
        assert "#27ae60" in style

    def test_validate_invalid_text_sets_red_border(self):
        ai = AnimatedInput("Label", "#333333", "placeholder")
        # Bypass validator to set invalid text directly
        ai.input.setValidator(None)
        ai.input.setText("abc")
        ai.validateInput()
        style = ai.input.styleSheet()
        assert "#e74c3c" in style

    def test_validate_empty_text_resets_border(self):
        ai = AnimatedInput("Label", "#333333", "placeholder")
        ai.input.setText("100")
        ai.validateInput()
        ai.input.setText("")
        ai.validateInput()
        style = ai.input.styleSheet()
        assert "transparent" in style


# ---------- MainWindow market data callback tests ----------

class TestMainWindowMarketData:
    def test_on_market_data_updates_rates(self, window):
        snapshot = {
            "rates_to_usd": {"BTC": 75000.0, "BRL": 0.15, "USD": 1.0, "EUR": 1.1, "COP": 0.00025, "PEN": 0.28, "ETH": 3500.0, "USDT": 1.0},
            "updated_at": "2026-01-01T00:00:00Z",
            "sources": {"crypto": "test", "fiat": "test"},
            "symbols": ["BTC", "ETH", "BRL", "USD"],
        }
        window._on_market_data(snapshot)
        assert window.current_rates_to_usd["BTC"] == 75000.0
        assert window.current_rates_to_usd["BRL"] == 0.15

    def test_on_market_data_updates_timestamp(self, window):
        snapshot = {
            "rates_to_usd": {"USD": 1.0},
            "updated_at": "2026-06-15T12:00:00Z",
            "sources": {"crypto": "live-src", "fiat": "live-src"},
            "symbols": ["USD"],
        }
        window._on_market_data(snapshot)
        assert window.last_market_timestamp == "2026-06-15T12:00:00Z"

    def test_on_market_data_live_source_sets_live_dot(self, window):
        snapshot = {
            "rates_to_usd": {"USD": 1.0},
            "updated_at": "2026-06-15T12:00:00Z",
            "sources": {"crypto": "coingecko", "fiat": "frankfurter"},
            "symbols": ["USD"],
        }
        window._on_market_data(snapshot)
        assert "vivo" in window.status_dot.text.text() or "Ao vivo" in window.status_dot.text.text()

    def test_on_market_data_static_fallback_sets_offline_dot(self, window):
        snapshot = {
            "rates_to_usd": {"USD": 1.0},
            "updated_at": "2026-01-01T00:00:00Z",
            "sources": {"crypto": "static-fallback", "fiat": "static-fallback"},
            "symbols": ["USD"],
        }
        window._on_market_data(snapshot)
        assert "Offline" in window.status_dot.text.text()

    def test_on_market_fetch_failed_sets_offline_dot(self, window):
        window.status_dot.set_state(StatusDot.LIVE)
        window._on_market_fetch_failed()
        assert "Offline" in window.status_dot.text.text()

    def test_on_market_fetch_failed_clears_in_progress_flag(self, window):
        window._refresh_in_progress = True
        window._on_market_fetch_failed()
        assert not window._refresh_in_progress

    def test_build_market_info_text_contains_rates(self, window):
        info = window._build_market_info_text()
        assert "BTC" in info
        assert "ETH" in info
        assert "USD" in info

    def test_build_market_info_text_with_timestamp(self, window):
        window.last_market_timestamp = "2026-01-01T00:00:00Z"
        info = window._build_market_info_text()
        assert "2026-01-01T00:00:00Z" in info

