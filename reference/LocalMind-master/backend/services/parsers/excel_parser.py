"""Excel and CSV file parser."""

from pathlib import Path
from typing import Any

import pandas as pd


def parse_excel(file_path: Path, rows_per_chunk: int = 20) -> list[dict[str, Any]]:
    """
    Parse Excel or CSV files, chunking by rows with headers.

    Args:
        file_path: Path to the Excel/CSV file.
        rows_per_chunk: Number of rows per chunk (default 20).

    Returns:
        List of chunks with text and metadata.
    """
    suffix = file_path.suffix.lower()
    chunks = []

    try:
        if suffix == ".csv":
            sheets = {"Sheet1": pd.read_csv(file_path)}
        else:
            # Excel file - read all sheets
            sheets = pd.read_excel(file_path, sheet_name=None, engine="openpyxl")
    except Exception as e:
        raise ValueError(f"Failed to read spreadsheet: {e}") from e

    for sheet_name, df in sheets.items():
        if df.empty:
            continue

        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]
        columns = list(df.columns)
        columns_str = ", ".join(columns)

        # Chunk by rows
        for start_idx in range(0, len(df), rows_per_chunk):
            end_idx = min(start_idx + rows_per_chunk, len(df))
            chunk_df = df.iloc[start_idx:end_idx]

            # Format rows as text
            rows_text = []
            for _, row in chunk_df.iterrows():
                row_values = [f"{col}: {val}" for col, val in row.items() if pd.notna(val)]
                rows_text.append(" | ".join(row_values))

            if rows_text:
                text = f"Sheet: {sheet_name} | Columns: {columns_str}\n\n"
                text += "\n".join(rows_text)

                chunks.append(
                    {
                        "text": text,
                        "metadata": {
                            "source": file_path.name,
                            "file_type": "excel" if suffix != ".csv" else "csv",
                            "page_or_sheet_or_slide": sheet_name,
                            "row_range": f"{start_idx + 1}-{end_idx}",
                        },
                    }
                )

    return chunks
