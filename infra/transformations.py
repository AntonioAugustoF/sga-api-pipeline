import pandas as pd

def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercases and strips whitespace from all column names."""
    df.columns = df.columns.str.lower().str.strip()
    return df


def remove_duplicates(df: pd.DataFrame, subset: list[str]) -> pd.DataFrame:
    """Remove duplicate rows based on the given subset of columns."""
    return df.drop_duplicates(subset=subset)


def remove_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows where all values are null."""
    return df.dropna(how="all")


def cast_string_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Converts the given columns to a string type and strips whitespace and lowercases."""
    df[columns] = df[columns].apply(
        lambda col: col.astype(str).str.strip().str.lower()
    )
    return df


def cast_date_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Converts the given columns to datetime, coercing erros to NaT."""
    for col in columns:
        parsed = pd.to_datetime(df[col], errors="coerce", utc=True).dt.tz_convert(None)
        df[col] = parsed.apply(lambda x: x.date() if pd.notna(x) else None)
    return df


def cast_numeric_columns(df: pd.DataFrame, columns: list[str], dtype: str = "float") -> pd.DataFrame:
    """Converts the given columns to a numeric type, coercing errors to NaN."""
    for col in columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df