import pandas as pd
from io import BytesIO


def generate_excel(results: list):
    """
    Generate Excel file in memory
    """

    df = pd.DataFrame(results)

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="News Summary")

    output.seek(0)

    return output
