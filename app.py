<<<<<<< HEAD
import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.express as px

# --------------------------------------------------
# Page setup
# --------------------------------------------------
st.set_page_config(page_title="AFPLAB CSV Processor", layout="wide")
st.title("AFPLAB CSV Processing App")

# --------------------------------------------------
# 1. File uploader
# --------------------------------------------------
uploaded_files = st.file_uploader(
    "Upload AFPLAB CSV files (multiple allowed)",
    type="csv",
    accept_multiple_files=True
)

if uploaded_files:

    # --------------------------------------------------
    # 2. Load & combine CSV files
    # --------------------------------------------------
    dfs = [pd.read_csv(io.BytesIO(f.read()), low_memory=False) for f in uploaded_files]
    combined_df = pd.concat(dfs, ignore_index=True)

    # --------------------------------------------------
    # 3. Required columns check
    # --------------------------------------------------
    required_cols = [
        "IDCODE","P11","P12","P21","P22","P31","P32","ENTERO1","ENTERO2","PROVINCE"
    ]

    missing = [c for c in required_cols if c not in combined_df.columns]
    if missing:
        st.error(f"Missing columns: {missing}")
        st.stop()

    # --------------------------------------------------
    # 4. Fix numeric data types
    # --------------------------------------------------
    num_cols = ["P11","P12","P21","P22","P31","P32","ENTERO1","ENTERO2"]
    combined_df[num_cols] = combined_df[num_cols].apply(
        pd.to_numeric, errors="coerce"
    ).astype("Int64")

    # --------------------------------------------------
    # 5. IDCODE2
    # --------------------------------------------------
    combined_df["IDCODE2"] = (
        combined_df["IDCODE"]
        .astype(str)
        .str.split("-", n=1)
        .str[0]
    )

    # --------------------------------------------------
    # 6. Year extraction
    # --------------------------------------------------
    def extract_year(idcode):
        if pd.isna(idcode):
            return ""
        parts = str(idcode).split("/")
        return "20" + parts[2] if len(parts) >= 3 else ""

    combined_df["Year"] = combined_df["IDCODE"].apply(extract_year)

    # --------------------------------------------------
    # 7. Build Type function
    # --------------------------------------------------
    def build_type(df, col1, col2, mapping):
        def _f(row):
            v1, v2 = row[col1], row[col2]
            if pd.notna(v1) and pd.notna(v2) and v1 == v2:
                return mapping.get(int(v1), "")
            return " + ".join(filter(None, [
                mapping.get(int(v1), "") if pd.notna(v1) else "",
                mapping.get(int(v2), "") if pd.notna(v2) else ""
            ]))
        return df.apply(_f, axis=1)

    # --------------------------------------------------
    # 8. Type mappings
    # --------------------------------------------------
    mapping_type1 = {1:"WPV1",2:"SL1",3:"WPV1+SL1",4:"VDPV1",5:"DISCORDANT",
                     6:"ITD Pending",7:"Negative",8:"Under Process",9:"Not received in Lab",
                     11:"aVDPV1",12:"iVDPV1",13:"cVDPV1"}
    mapping_type2 = {1:"WPV2",2:"SL2",3:"WPV2+SL2",4:"VDPV2",5:"DISCORDANT",
                     6:"ITD Pending",7:"Negative",8:"Under Process",9:"Not received in Lab",
                     11:"aVDPV2",12:"iVDPV2",13:"cVDPV2"}
    mapping_type3 = {1:"WPV3",2:"SL3",3:"WPV3+SL3",4:"VDPV3",5:"DISCORDANT",
                     6:"ITD Pending",7:"Negative",8:"Under Process",9:"Not received in Lab",
                     11:"aVDPV3",12:"iVDPV3",13:"cVDPV3"}

    # --------------------------------------------------
    # 9. Create type columns
    # --------------------------------------------------
    combined_df["type1"] = build_type(combined_df, "P11","P12", mapping_type1)
    combined_df["type2"] = build_type(combined_df, "P21","P22", mapping_type2)
    combined_df["type3"] = build_type(combined_df, "P31","P32", mapping_type3)

    # --------------------------------------------------
    # 10. ENTERO column
    # --------------------------------------------------
    entero_map = {1:"NPEV",7:"NVI",8:"Under Process"}
    def build_entero(row):
        e1, e2 = row["ENTERO1"], row["ENTERO2"]
        if pd.notna(e1) and pd.notna(e2) and e1 == e2:
            return entero_map.get(int(e1), "")
        if (pd.notna(e1) and e1 == 1) or (pd.notna(e2) and e2 == 1):
            return "NPEV"
        return " + ".join(filter(None, [
            entero_map.get(int(e1), "") if pd.notna(e1) else "",
            entero_map.get(int(e2), "") if pd.notna(e2) else ""
        ]))
    combined_df["ENTERO"] = combined_df.apply(build_entero, axis=1)

    # --------------------------------------------------
    # 11. RESULT column
    # --------------------------------------------------
    def contains(text, keyword):
        return keyword.lower() in str(text).lower()
    def build_result(row):
        t1, t2, t3 = row["type1"], row["type2"], row["type3"]
        entero = row["ENTERO"]
        if any(contains(x, "Not received in Lab") for x in [t1, t2, t3, entero]):
            return "Not received in Lab"
        parts = []
        if contains(t1, "SL1"): parts.append("SL1")
        if contains(t1, "WPV1"): parts.append("WPV1")
        if contains(t2, "SL2"): parts.append("SL2")
        if contains(t2, "WPV2"): parts.append("WPV2")
        if contains(t3, "SL3"): parts.append("SL3")
        if contains(t3, "WPV3"): parts.append("WPV3")
        if contains(entero, "NPEV"): parts.append("NPEV")
        for txt, n in [(t1,1),(t2,2),(t3,3)]:
            if contains(txt,"iVDPV"): parts.append(f"iVDPV{n}")
            if contains(txt,"cVDPV"): parts.append(f"cVDPV{n}")
            if contains(txt,"aVDPV"): parts.append(f"aVDPV{n}")
            if contains(txt,"VDPV") and not any(contains(txt,x) for x in ["iVDPV","cVDPV","aVDPV"]):
                parts.append(f"VDPV{n}")
        parts = list(dict.fromkeys(parts))
        if not parts:
            return "NVI" if contains(entero, "NVI") else "Under Process"
        return " + ".join(parts)
    combined_df["RESULT"] = combined_df.apply(build_result, axis=1)

    # --------------------------------------------------
    # 12. WPV1count
    # --------------------------------------------------
    combined_df["WPV1count"] = combined_df["RESULT"].astype(str).str.contains(r"\bWPV1\b", na=False).astype(int)

    # --------------------------------------------------
    # 13. Linelist
    # --------------------------------------------------
    combined_df["Linelist"] = 0
    idx = combined_df[combined_df["WPV1count"] == 1].groupby("IDCODE2").head(1).index
    combined_df.loc[idx, "Linelist"] = 1

    # --------------------------------------------------
    # 14. Preview & download
    # --------------------------------------------------
    st.success("Processing completed successfully")
    st.dataframe(combined_df.head(25))

    csv = combined_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Processed CSV",
        csv,
        "AFPLAB_Combined.csv",
        "text/csv"
    )

    # --------------------------------------------------
    # 15. AFPLAB Dashboard
    # --------------------------------------------------
    st.markdown("---")
    st.header("AFPLAB Dashboard")

    # Filters
    st.sidebar.header("Dashboard Filters")
    provinces = st.sidebar.multiselect(
        "Select Province(s)", options=combined_df["PROVINCE"].unique(), 
        default=combined_df["PROVINCE"].unique()
    )
    years = st.sidebar.multiselect(
        "Select Year(s)", options=combined_df["Year"].unique(),
        default=combined_df["Year"].unique()
    )

    filtered_df = combined_df[(combined_df["PROVINCE"].isin(provinces)) & (combined_df["Year"].isin(years))]

    # Metrics
    col1, col2 = st.columns(2)
    col1.metric("Total WPV1 Cases", int(filtered_df["WPV1count"].sum()))
    col2.metric("Total Linelist Cases", int(filtered_df["Linelist"].sum()))

    # WPV1 by Province
    wpv1_province = filtered_df.groupby("PROVINCE")["WPV1count"].sum().reset_index()
    fig1 = px.bar(wpv1_province, x="PROVINCE", y="WPV1count", text="WPV1count", title="WPV1 Cases by Province")
    fig1.update_traces(textposition="outside")
    st.plotly_chart(fig1, use_container_width=True)

    # Linelist by Province and Year (Stacked)
    linelist_df = filtered_df.groupby(["Year","PROVINCE"])["Linelist"].sum().reset_index()
    fig2 = px.bar(linelist_df, x="PROVINCE", y="Linelist", color="Year", text="Linelist", title="Linelist by Province and Year")
    fig2.update_traces(textposition="outside")
    st.plotly_chart(fig2, use_container_width=True)

    # Preview filtered dashboard data
    st.subheader("Filtered Dashboard Data Preview")
    st.dataframe(filtered_df.head(25))

=======
import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.express as px

# --------------------------------------------------
# Page setup
# --------------------------------------------------
st.set_page_config(page_title="AFPLAB CSV Processor", layout="wide")
st.title("AFPLAB CSV Processing App")

# --------------------------------------------------
# 1. File uploader
# --------------------------------------------------
uploaded_files = st.file_uploader(
    "Upload AFPLAB CSV files (multiple allowed)",
    type="csv",
    accept_multiple_files=True
)

if uploaded_files:

    # --------------------------------------------------
    # 2. Load & combine CSV files
    # --------------------------------------------------
    dfs = [pd.read_csv(io.BytesIO(f.read()), low_memory=False) for f in uploaded_files]
    combined_df = pd.concat(dfs, ignore_index=True)

    # --------------------------------------------------
    # 3. Required columns check
    # --------------------------------------------------
    required_cols = [
        "IDCODE","P11","P12","P21","P22","P31","P32","ENTERO1","ENTERO2","PROVINCE"
    ]

    missing = [c for c in required_cols if c not in combined_df.columns]
    if missing:
        st.error(f"Missing columns: {missing}")
        st.stop()

    # --------------------------------------------------
    # 4. Fix numeric data types
    # --------------------------------------------------
    num_cols = ["P11","P12","P21","P22","P31","P32","ENTERO1","ENTERO2"]
    combined_df[num_cols] = combined_df[num_cols].apply(
        pd.to_numeric, errors="coerce"
    ).astype("Int64")

    # --------------------------------------------------
    # 5. IDCODE2
    # --------------------------------------------------
    combined_df["IDCODE2"] = (
        combined_df["IDCODE"]
        .astype(str)
        .str.split("-", n=1)
        .str[0]
    )

    # --------------------------------------------------
    # 6. Year extraction
    # --------------------------------------------------
    def extract_year(idcode):
        if pd.isna(idcode):
            return ""
        parts = str(idcode).split("/")
        return "20" + parts[2] if len(parts) >= 3 else ""

    combined_df["Year"] = combined_df["IDCODE"].apply(extract_year)

    # --------------------------------------------------
    # 7. Build Type function
    # --------------------------------------------------
    def build_type(df, col1, col2, mapping):
        def _f(row):
            v1, v2 = row[col1], row[col2]
            if pd.notna(v1) and pd.notna(v2) and v1 == v2:
                return mapping.get(int(v1), "")
            return " + ".join(filter(None, [
                mapping.get(int(v1), "") if pd.notna(v1) else "",
                mapping.get(int(v2), "") if pd.notna(v2) else ""
            ]))
        return df.apply(_f, axis=1)

    # --------------------------------------------------
    # 8. Type mappings
    # --------------------------------------------------
    mapping_type1 = {1:"WPV1",2:"SL1",3:"WPV1+SL1",4:"VDPV1",5:"DISCORDANT",
                     6:"ITD Pending",7:"Negative",8:"Under Process",9:"Not received in Lab",
                     11:"aVDPV1",12:"iVDPV1",13:"cVDPV1"}
    mapping_type2 = {1:"WPV2",2:"SL2",3:"WPV2+SL2",4:"VDPV2",5:"DISCORDANT",
                     6:"ITD Pending",7:"Negative",8:"Under Process",9:"Not received in Lab",
                     11:"aVDPV2",12:"iVDPV2",13:"cVDPV2"}
    mapping_type3 = {1:"WPV3",2:"SL3",3:"WPV3+SL3",4:"VDPV3",5:"DISCORDANT",
                     6:"ITD Pending",7:"Negative",8:"Under Process",9:"Not received in Lab",
                     11:"aVDPV3",12:"iVDPV3",13:"cVDPV3"}

    # --------------------------------------------------
    # 9. Create type columns
    # --------------------------------------------------
    combined_df["type1"] = build_type(combined_df, "P11","P12", mapping_type1)
    combined_df["type2"] = build_type(combined_df, "P21","P22", mapping_type2)
    combined_df["type3"] = build_type(combined_df, "P31","P32", mapping_type3)

    # --------------------------------------------------
    # 10. ENTERO column
    # --------------------------------------------------
    entero_map = {1:"NPEV",7:"NVI",8:"Under Process"}
    def build_entero(row):
        e1, e2 = row["ENTERO1"], row["ENTERO2"]
        if pd.notna(e1) and pd.notna(e2) and e1 == e2:
            return entero_map.get(int(e1), "")
        if (pd.notna(e1) and e1 == 1) or (pd.notna(e2) and e2 == 1):
            return "NPEV"
        return " + ".join(filter(None, [
            entero_map.get(int(e1), "") if pd.notna(e1) else "",
            entero_map.get(int(e2), "") if pd.notna(e2) else ""
        ]))
    combined_df["ENTERO"] = combined_df.apply(build_entero, axis=1)

    # --------------------------------------------------
    # 11. RESULT column
    # --------------------------------------------------
    def contains(text, keyword):
        return keyword.lower() in str(text).lower()
    def build_result(row):
        t1, t2, t3 = row["type1"], row["type2"], row["type3"]
        entero = row["ENTERO"]
        if any(contains(x, "Not received in Lab") for x in [t1, t2, t3, entero]):
            return "Not received in Lab"
        parts = []
        if contains(t1, "SL1"): parts.append("SL1")
        if contains(t1, "WPV1"): parts.append("WPV1")
        if contains(t2, "SL2"): parts.append("SL2")
        if contains(t2, "WPV2"): parts.append("WPV2")
        if contains(t3, "SL3"): parts.append("SL3")
        if contains(t3, "WPV3"): parts.append("WPV3")
        if contains(entero, "NPEV"): parts.append("NPEV")
        for txt, n in [(t1,1),(t2,2),(t3,3)]:
            if contains(txt,"iVDPV"): parts.append(f"iVDPV{n}")
            if contains(txt,"cVDPV"): parts.append(f"cVDPV{n}")
            if contains(txt,"aVDPV"): parts.append(f"aVDPV{n}")
            if contains(txt,"VDPV") and not any(contains(txt,x) for x in ["iVDPV","cVDPV","aVDPV"]):
                parts.append(f"VDPV{n}")
        parts = list(dict.fromkeys(parts))
        if not parts:
            return "NVI" if contains(entero, "NVI") else "Under Process"
        return " + ".join(parts)
    combined_df["RESULT"] = combined_df.apply(build_result, axis=1)

    # --------------------------------------------------
    # 12. WPV1count
    # --------------------------------------------------
    combined_df["WPV1count"] = combined_df["RESULT"].astype(str).str.contains(r"\bWPV1\b", na=False).astype(int)

    # --------------------------------------------------
    # 13. Linelist
    # --------------------------------------------------
    combined_df["Linelist"] = 0
    idx = combined_df[combined_df["WPV1count"] == 1].groupby("IDCODE2").head(1).index
    combined_df.loc[idx, "Linelist"] = 1

    # --------------------------------------------------
    # 14. Preview & download
    # --------------------------------------------------
    st.success("Processing completed successfully")
    st.dataframe(combined_df.head(25))

    csv = combined_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Processed CSV",
        csv,
        "AFPLAB_Combined.csv",
        "text/csv"
    )

    # --------------------------------------------------
    # 15. AFPLAB Dashboard
    # --------------------------------------------------
    st.markdown("---")
    st.header("AFPLAB Dashboard")

    # Filters
    st.sidebar.header("Dashboard Filters")
    provinces = st.sidebar.multiselect(
        "Select Province(s)", options=combined_df["PROVINCE"].unique(), 
        default=combined_df["PROVINCE"].unique()
    )
    years = st.sidebar.multiselect(
        "Select Year(s)", options=combined_df["Year"].unique(),
        default=combined_df["Year"].unique()
    )

    filtered_df = combined_df[(combined_df["PROVINCE"].isin(provinces)) & (combined_df["Year"].isin(years))]

    # Metrics
    col1, col2 = st.columns(2)
    col1.metric("Total WPV1 Cases", int(filtered_df["WPV1count"].sum()))
    col2.metric("Total Linelist Cases", int(filtered_df["Linelist"].sum()))

    # WPV1 by Province
    wpv1_province = filtered_df.groupby("PROVINCE")["WPV1count"].sum().reset_index()
    fig1 = px.bar(wpv1_province, x="PROVINCE", y="WPV1count", text="WPV1count", title="WPV1 Cases by Province")
    fig1.update_traces(textposition="outside")
    st.plotly_chart(fig1, use_container_width=True)

    # Linelist by Province and Year (Stacked)
    linelist_df = filtered_df.groupby(["Year","PROVINCE"])["Linelist"].sum().reset_index()
    fig2 = px.bar(linelist_df, x="PROVINCE", y="Linelist", color="Year", text="Linelist", title="Linelist by Province and Year")
    fig2.update_traces(textposition="outside")
    st.plotly_chart(fig2, use_container_width=True)

    # Preview filtered dashboard data
    st.subheader("Filtered Dashboard Data Preview")
    st.dataframe(filtered_df.head(25))

>>>>>>> afbdcac (Add Streamlit app with Python 3.10 runtime)
