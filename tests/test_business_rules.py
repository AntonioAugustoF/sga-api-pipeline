import datetime
import pandas as pd

from transform.business_rules import (
    calculate_days_overdue,
    classify_aging_bucket,
    classify_payment_status,
    calculate_payment_difference,
    calculate_age,
    allocate_invoice_value_by_vehicle,
)


def test_calculate_days_overdue_computes_positive_gap():
    reference_date = datetime.date(2026, 6, 30)
    due_dates = pd.Series([datetime.date(2026, 6, 1)])
    result = calculate_days_overdue(due_dates, reference_date)
    assert result.iloc[0] == 29


def test_calculate_days_overdue_floors_future_due_dates_at_zero():
    reference_date = datetime.date(2026, 6, 1)
    due_dates = pd.Series([datetime.date(2026, 6, 30)])
    result = calculate_days_overdue(due_dates, reference_date)
    assert result.iloc[0] == 0


def test_calculate_days_overdue_preserves_nulls():
    reference_date = datetime.date(2026, 6, 30)
    due_dates = pd.Series([None])
    result = calculate_days_overdue(due_dates, reference_date)
    assert result.iloc[0] is None


def test_classify_aging_bucket_boundaries():
    days = pd.Series([0, 30, 31, 60, 61, 90, 91, None])
    result = classify_aging_bucket(days)
    assert result.tolist() == ["0-30", "0-30", "31-60", "31-60", "61-90", "61-90", "90+", None]


def test_classify_payment_status_unpaid():
    df = pd.DataFrame({"pago": ["n"], "valor_boleto": [100.0], "valor_pagamento": [0.0]})
    result = classify_payment_status(df, "pago", "valor_boleto", "valor_pagamento")
    assert result.iloc[0] == "nao_pago"


def test_classify_payment_status_paid_in_full():
    df = pd.DataFrame({"pago": ["y"], "valor_boleto": [100.0], "valor_pagamento": [100.0]})
    result = classify_payment_status(df, "pago", "valor_boleto", "valor_pagamento")
    assert result.iloc[0] == "pago_integral"


def test_classify_payment_status_paid_less_than_billed():
    df = pd.DataFrame({"pago": ["y"], "valor_boleto": [100.0], "valor_pagamento": [80.0]})
    result = classify_payment_status(df, "pago", "valor_boleto", "valor_pagamento")
    assert result.iloc[0] == "pago_a_menor"


def test_classify_payment_status_paid_more_than_billed():
    df = pd.DataFrame({"pago": ["y"], "valor_boleto": [100.0], "valor_pagamento": [120.0]})
    result = classify_payment_status(df, "pago", "valor_boleto", "valor_pagamento")
    assert result.iloc[0] == "pago_a_maior"


def test_calculate_payment_difference_is_signed():
    df = pd.DataFrame({"valor_boleto": [100.0], "valor_pagamento": [80.0]})
    result = calculate_payment_difference(df, "valor_boleto", "valor_pagamento")
    assert result.iloc[0] == -20.0


def test_calculate_age_before_birthday_in_reference_year():
    reference_date = datetime.date(2026, 6, 30)
    birth_dates = pd.Series([datetime.date(2000, 12, 1)])
    result = calculate_age(birth_dates, reference_date)
    assert result.iloc[0] == 25


def test_calculate_age_after_birthday_in_reference_year():
    reference_date = datetime.date(2026, 6, 30)
    birth_dates = pd.Series([datetime.date(2000, 1, 15)])
    result = calculate_age(birth_dates, reference_date)
    assert result.iloc[0] == 26


def test_calculate_age_on_birthday():
    reference_date = datetime.date(2026, 6, 30)
    birth_dates = pd.Series([datetime.date(2000, 6, 30)])
    result = calculate_age(birth_dates, reference_date)
    assert result.iloc[0] == 26


def test_calculate_age_preserves_nulls():
    reference_date = datetime.date(2026, 6, 30)
    birth_dates = pd.Series([None])
    result = calculate_age(birth_dates, reference_date)
    assert result.iloc[0] is None


def test_allocate_invoice_value_by_vehicle_single_vehicle_keeps_full_value():
    df = pd.DataFrame({
        "codigo_boleto": ["1"],
        "veiculo": [["100"]],
        "valor_boleto": [300.0],
    })
    result = allocate_invoice_value_by_vehicle(df, "codigo_boleto", "veiculo", "valor_boleto")
    assert result["codigo_veiculo"].tolist() == ["100"]
    assert result["valor_rateado"].tolist() == [300.0]
    assert result["qtd_veiculos_boleto"].tolist() == [1]


def test_allocate_invoice_value_by_vehicle_splits_evenly_across_vehicles():
    df = pd.DataFrame({
        "codigo_boleto": ["1"],
        "veiculo": [["100", "200", "300"]],
        "valor_boleto": [300.0],
    })
    result = allocate_invoice_value_by_vehicle(df, "codigo_boleto", "veiculo", "valor_boleto")
    assert sorted(result["codigo_veiculo"].tolist()) == ["100", "200", "300"]
    assert result["valor_rateado"].tolist() == [100.0, 100.0, 100.0]
    assert result["qtd_veiculos_boleto"].tolist() == [3, 3, 3]
    assert result["valor_rateado"].sum() == 300.0


def test_allocate_invoice_value_by_vehicle_drops_boletos_without_vehicles():
    df = pd.DataFrame({
        "codigo_boleto": ["1"],
        "veiculo": [[]],
        "valor_boleto": [150.0],
    })
    result = allocate_invoice_value_by_vehicle(df, "codigo_boleto", "veiculo", "valor_boleto")
    assert result.empty
