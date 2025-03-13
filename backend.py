from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import fitz
import io

app = FastAPI()

# CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store the uploaded dataframe in memory
dataframe = pd.DataFrame()

# Upload CSV and extract columns
@app.post("/upload/csv/")
async def upload_csv(file: UploadFile = File(...)):
    global dataframe
    try:
        contents = await file.read()
        dataframe = pd.read_csv(io.StringIO(contents.decode("utf-8")))

        if dataframe.empty:
            raise HTTPException(status_code=400, detail="Uploaded CSV is empty")

        labels = [
            {
                "column": col,
                "example": (
                    int(dataframe[col].iloc[0]) if isinstance(dataframe[col].iloc[0], (int, float))
                    else str(dataframe[col].iloc[0])
                ) if pd.notna(dataframe[col].iloc[0]) else None
            }
            for col in dataframe.columns
        ]

        aggregation_operations = ["sum", "mean", "min", "max", "count", "std"]
        window_operations = ["rolling_mean", "cumsum", "rank", "expanding_mean"]

        return {
            "filename": file.filename,
            "columns": dataframe.columns.tolist(),
            "labels": labels,
            "aggregation_operations": aggregation_operations,
            "window_operations": window_operations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Upload XLSX and extract columns
@app.post("/upload/xlsx/")
async def upload_xlsx(file: UploadFile = File(...)):
    global dataframe
    try:
        contents = await file.read()
        dataframe = pd.read_excel(io.BytesIO(contents))

        if dataframe.empty:
            raise HTTPException(status_code=400, detail="Uploaded XLSX is empty")

        labels = [
            {
                "column": col,
                "example": (
                    int(dataframe[col].iloc[0]) if isinstance(dataframe[col].iloc[0], (int, float))
                    else str(dataframe[col].iloc[0])
                ) if pd.notna(dataframe[col].iloc[0]) else None
            }
            for col in dataframe.columns
        ]

        aggregation_operations = ["sum", "mean", "min", "max", "count", "std"]
        window_operations = ["rolling_mean", "cumsum", "rank", "expanding_mean"]

        return {
            "filename": file.filename,
            "columns": dataframe.columns.tolist(),
            "labels": labels,
            "aggregation_operations": aggregation_operations,
            "window_operations": window_operations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Upload PDF and extract text
@app.post("/upload/pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        pdf = fitz.open(stream=contents, filetype="pdf")

        text = ""
        for page in pdf:
            text += page.get_text()

        if not text:
            raise HTTPException(status_code=400, detail="No text extracted from PDF")

        return {"filename": file.filename, "content": text[:500]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read PDF: {str(e)}")

# Typecasting endpoint
@app.post("/typecast/")
async def typecast(column_types: dict):
    global dataframe
    if dataframe.empty:
        raise HTTPException(status_code=400, detail="No file uploaded yet")

    errors = {}
    for column, dtype in column_types.items():
        if column not in dataframe.columns:
            errors[column] = "Column not found"
            continue

        try:
            # Clean up the column
            dataframe[column] = dataframe[column].astype(str).str.strip().replace(',', '.', regex=True)
            dataframe[column] = pd.to_numeric(dataframe[column], errors='coerce')

            if dtype == "No Change":
                pass
            elif dtype == "int":
                # Round floats to nearest integer before casting
                dataframe[column] = dataframe[column].round().astype("Int64")  # Handles NaNs correctly
            elif dtype == "float":
                dataframe[column] = dataframe[column].astype(float)
            elif dtype == "str":
                dataframe[column] = dataframe[column].astype(str)
            elif dtype == "datetime":
                dataframe[column] = pd.to_datetime(dataframe[column], errors="coerce")
            else:
                errors[column] = f"Unsupported type '{dtype}'"
        except Exception as e:
            errors[column] = str(e)

    if errors:
        raise HTTPException(status_code=400, detail=errors)

    return {"status": "success", "message": "Columns typecasted successfully"}


# Aggregate functions
@app.get("/aggregate/")
async def aggregate(column: str = Query(...), operation: str = Query(...)):
    global dataframe
    if dataframe is None or dataframe.empty:
        raise HTTPException(status_code=400, detail="No file uploaded yet")

    if column not in dataframe.columns:
        raise HTTPException(status_code=404, detail=f"Column '{column}' not found")

    # Ensure column is numeric before aggregating
    try:
        dataframe[column] = pd.to_numeric(dataframe[column], errors='coerce')  # Ensure numeric type
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to convert column '{column}' to numeric: {e}")

    # Drop NaNs to avoid aggregation errors
    valid_data = dataframe[column].dropna()

    if valid_data.empty:
        raise HTTPException(status_code=400, detail=f"Column '{column}' contains no valid numeric data")

    try:
        if operation == "sum":
            result = valid_data.sum()
        elif operation == "mean":
            result = valid_data.mean()
        elif operation == "min":
            result = valid_data.min()
        elif operation == "max":
            result = valid_data.max()
        elif operation == "count":
            result = valid_data.count()
        elif operation == "std":
            result = valid_data.std()
        else:
            raise HTTPException(status_code=400, detail=f"Operation '{operation}' not supported")

        return {"column": column, "operation": operation, "result": result}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Aggregation error: {e}")


# Window functions
@app.get("/window/")
async def window(column: str, window_size: int, operation: str):
    if dataframe.empty:
        raise HTTPException(status_code=400, detail="No file uploaded yet")

    if column not in dataframe.columns:
        raise HTTPException(status_code=404, detail=f"Column '{column}' not found")

    if not pd.api.types.is_numeric_dtype(dataframe[column]):
        raise HTTPException(status_code=400, detail=f"Column '{column}' is not numeric")

    try:
        if operation == "rolling_mean":
            result = dataframe[column].rolling(window=window_size).mean().tolist()
        elif operation == "cumsum":
            result = dataframe[column].cumsum().tolist()
        elif operation == "rank":
            result = dataframe[column].rank().tolist()
        elif operation == "expanding_mean":
            result = dataframe[column].expanding().mean().tolist()
        else:
            raise HTTPException(status_code=400, detail=f"Operation '{operation}' not supported")

        return {"column": column, "operation": operation, "result": result}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Start the backend:
# uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
