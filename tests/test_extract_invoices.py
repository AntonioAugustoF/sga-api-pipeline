import pytest

from extract.extract_invoices import merge_by_invoice


def test_merge_by_invoice_lets_the_later_window_win():
    merged = merge_by_invoice([{"codigo_boleto": "1", "v": "new"}], [{"codigo_boleto": "1", "v": "paid"}])
    assert merged == [{"codigo_boleto": "1", "v": "paid"}]


def test_merge_by_invoice_refuses_an_invoice_without_key():
    """Keyed under None, every keyless invoice would collapse into one row."""
    with pytest.raises(ValueError, match="without codigo_boleto"):
        merge_by_invoice([{"codigo_boleto": "1"}, {"x": 1}, {"x": 2}])
