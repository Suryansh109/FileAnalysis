import streamlit as st
import requests
import pandas as pd

st.title("📂 File Upload Service")

# Upload file section
uploaded_file = st.file_uploader("Choose a CSV, XLSX, or PDF file", type=["csv", "xlsx", "pdf"])

if uploaded_file:
    file_type = uploaded_file.name.split(".")[-1]

    if file_type in ["csv", "xlsx"]:
        files = {"file": uploaded_file.getvalue()}
        url = f"https://fileanalysis.onrender.com/upload/{file_type}/"
        response = requests.post(url, files=files)
        
        if response.status_code == 200:
            data = response.json()
            st.success(f"✅ {data['filename']} uploaded successfully!")
            st.write("### 🏷️ Extracted Labels:")
            for label in data['labels']:
                st.write(f"- **{label['column']}** → Example: `{label['example']}`")

            # Typecasting section
            st.write("### 🔀 Typecast Columns:")
            dtype_map = {}
            dtype_options = ["No Change","int", "float", "str", "datetime"]

            for col in data['columns']:
                dtype_map[col] = st.selectbox(
                    f"Select type for `{col}`",
                    dtype_options,
                    key=f"dtype_{col}"
                )

            if st.button("Apply Typecasting"):
                typecast_response = requests.post(
                    "https://fileanalysis.onrender.com/typecast/",
                    json=dtype_map
                )

                if typecast_response.status_code == 200:
                    st.success("✅ Typecasting applied successfully!")
                else:
                    errors = typecast_response.json().get("detail", "Unknown error occurred")
                    if isinstance(errors, dict):
                        for col, error in errors.items():
                            st.error(f"**{col}** → {error}")
                    else:
                        st.error(errors)

            # Show available operations
            st.write("### 🔢 Aggregation Operations:")
            st.write(", ".join(data["aggregation_operations"]))

            st.write("### 🔄 Window Operations:")
            st.write(", ".join(data["window_operations"]))

            # Basic operations
            if st.button("Show Data Preview"):
                if file_type == "csv":
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                st.write(df)

            # Aggregate
            st.write("### 📊 Perform Aggregation:")
            column = st.selectbox("Select column for aggregation", data["columns"])
            operation = st.selectbox("Select aggregation operation", data["aggregation_operations"])
            if st.button("Aggregate"):
                agg_response = requests.get(
                    "https://fileanalysis.onrender.com/aggregate/",
                    params={"column": column, "operation": operation},
                )
                if agg_response.status_code == 200:
                    result = agg_response.json()
                    st.success(f"{operation.capitalize()} of `{column}`: `{result['result']}`")
                else:
                    error = agg_response.json().get("detail", "Unknown error occurred")
                    st.error(error)

            # Window
            st.write("### 🪟 Perform Window Operation:")
            column = st.selectbox("Select column for window operation", data["columns"], key="window_column")
            operation = st.selectbox("Select window operation", data["window_operations"], key="window_operation")
            window_size = st.number_input("Window size", min_value=1, value=3, step=1)
            if st.button("Apply Window Operation"):
                window_response = requests.get(
                    "https://fileanalysis.onrender.com/window/",
                    params={"column": column, "operation": operation, "window_size": window_size},
                )
                if window_response.status_code == 200:
                    result = window_response.json()
                    st.write(f"{operation.capitalize()} of `{column}`:")
                    st.write(result["result"])
                else:
                    error = window_response.json().get("detail", "Unknown error occurred")
                    st.error(error)

    elif file_type == "pdf":
        files = {"file": uploaded_file.getvalue()}
        response = requests.post("https://fileanalysis.onrender.com/upload/pdf/", files=files)
        if response.status_code == 200:
            data = response.json()
            st.success(f"✅ {data['filename']} uploaded successfully!")
            st.write("### 📝 Extracted Content:")
            st.write(data['content'])

# Start the frontend:
# streamlit run frontend.py
