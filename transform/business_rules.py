import datetime
import pandas as pd


def calculate_days_overdue(due_dates: pd.Series, reference_date: datetime.date) -> pd.Series:
    """Days between reference_date and each due date, floored at 0. Null due dates stay null."""
    def _days(due):
        if pd.isna(due):
            return None
        return max((reference_date - due).days, 0)

    return due_dates.apply(_days)


def classify_aging_bucket(days_overdue: pd.Series) -> pd.Series:
    """Buckets days-overdue into the aging ranges used for delinquency reporting."""
    def _bucket(days):
        if pd.isna(days):
            return None
        if days <= 30:
            return "0-30"
        if days <= 60:
            return "31-60"
        if days <= 90:
            return "61-90"
        return "90+"

    return days_overdue.apply(_bucket)


def classify_payment_status(df: pd.DataFrame, paid_flag_col: str, invoice_value_col: str, paid_value_col: str) -> pd.Series:
    """Reconciles invoice value against amount paid: nao_pago, pago_integral, pago_a_menor, pago_a_maior."""
    def _status(row):
        if row[paid_flag_col] != "y":
            return "nao_pago"
        diff = row[paid_value_col] - row[invoice_value_col]
        if abs(diff) < 0.01:
            return "pago_integral"
        return "pago_a_menor" if diff < 0 else "pago_a_maior"

    return df.apply(_status, axis=1)


def calculate_payment_difference(df: pd.DataFrame, invoice_value_col: str, paid_value_col: str) -> pd.Series:
    """Signed difference between amount paid and amount billed (negative means paid less than billed)."""
    return df[paid_value_col] - df[invoice_value_col]


def calculate_age(birth_dates: pd.Series, reference_date: datetime.date) -> pd.Series:
    """Age in full years as of reference_date. Null birth dates stay null."""
    def _age(birth_date):
        if pd.isna(birth_date):
            return None
        years = reference_date.year - birth_date.year
        if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
            years -= 1
        return years

    return birth_dates.apply(_age)
