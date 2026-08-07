from __future__ import annotations

import importlib.util
import os
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
FINAL_OUTPUT = ROOT / "output" / "augmented-companies.xlsx"
STARTER_FILE = ROOT / "data" / "starter-companies.csv"
AGENT_FILE = ROOT / "src" / "augment_companies.py"

# The augmentation module uses repository-relative file paths for its cache.
os.chdir(ROOT)


@st.cache_resource
def load_agent_module():
    spec = importlib.util.spec_from_file_location("augment_companies_agent", AGENT_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load src/augment_companies.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@st.cache_data
def load_final_dataset() -> pd.DataFrame:
    if not FINAL_OUTPUT.exists():
        return pd.DataFrame()
    return pd.read_excel(FINAL_OUTPUT)


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Augmented Companies")
    return output.getvalue()


def normalize_uploaded_csv(uploaded_file) -> pd.DataFrame:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    if "company_name" not in df.columns:
        raise ValueError("The CSV must contain a column named 'company_name'.")
    df["company_name"] = df["company_name"].astype(str).str.strip()
    df = df[df["company_name"] != ""].copy()
    return df


st.set_page_config(
    page_title="AI Data Augmentor",
    page_icon="🔎",
    layout="wide",
)

st.title("AI Data Augmentor")
st.caption(
    "A lightweight UI for exploring the validated dataset and safely testing the data-augmentation agent."
)

final_df = load_final_dataset()

if not final_df.empty:
    total_companies = len(final_df)
    unknown_cells = int(
        final_df[[c for c in ["Website", "Phone", "Location"] if c in final_df.columns]]
        .astype(str)
        .apply(lambda col: col.str.upper().eq("UNKNOWN"))
        .sum()
        .sum()
    )
    completed_cells = total_companies * 3 - unknown_cells

    c1, c2, c3 = st.columns(3)
    c1.metric("Companies", total_companies)
    c2.metric("Verified data fields", completed_cells)
    c3.metric("UNKNOWN fields", unknown_cells)


tab_dataset, tab_agent, tab_workflow = st.tabs(
    ["Final Dataset", "Try the Agent", "How It Works"]
)


with tab_dataset:
    st.subheader("Validated final dataset")
    st.write(
        "This is the submission dataset after automated enrichment and human QA. "
        "UNKNOWN is retained when a value could not be verified reliably."
    )

    if final_df.empty:
        st.warning("Final dataset was not found in output/augmented-companies.xlsx.")
    else:
        search = st.text_input(
            "Filter companies",
            placeholder="Example: Patagonia, Garmin, Marmot",
        )

        display_df = final_df.copy()
        if search.strip():
            mask = display_df["company_name"].astype(str).str.contains(
                search.strip(), case=False, na=False
            )
            display_df = display_df[mask]

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.download_button(
            "Download final Excel",
            data=FINAL_OUTPUT.read_bytes(),
            file_name="augmented-companies.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=False,
        )


with tab_agent:
    st.subheader("Try the augmentation agent")
    st.info(
        "For a responsive classroom demo, the UI processes a maximum of 5 companies per run. "
        "The full 50-company dataset is available in the Final Dataset tab."
    )

    uploaded = st.file_uploader(
        "Upload a CSV with a company_name column",
        type=["csv"],
    )

    if uploaded is None:
        if STARTER_FILE.exists():
            st.caption("No file uploaded. You can use the included starter dataset instead.")
            if st.button("Load starter companies"):
                st.session_state["demo_df"] = pd.read_csv(STARTER_FILE)
    else:
        try:
            st.session_state["demo_df"] = normalize_uploaded_csv(uploaded)
        except Exception as exc:
            st.error(str(exc))

    demo_df = st.session_state.get("demo_df")

    if isinstance(demo_df, pd.DataFrame) and not demo_df.empty:
        st.write(f"Loaded **{len(demo_df)}** companies.")
        st.dataframe(demo_df.head(20), use_container_width=True, hide_index=True)

        names = demo_df["company_name"].astype(str).tolist()
        default_selection = names[: min(3, len(names))]

        selected = st.multiselect(
            "Choose up to 5 companies to test",
            options=names,
            default=default_selection,
            max_selections=5,
        )

        if st.button("Run augmentation", type="primary", disabled=not selected):
            agent = load_agent_module()
            rows = []
            progress = st.progress(0)
            status = st.empty()

            for i, company in enumerate(selected, start=1):
                status.write(f"Researching {i}/{len(selected)}: **{company}**")

                try:
                    website, phone, location, source = agent.process_company(
                        company,
                        "UNKNOWN",
                        "UNKNOWN",
                        "UNKNOWN",
                    )
                except Exception as exc:
                    website = phone = location = "UNKNOWN"
                    source = f"ERROR: {exc}"

                rows.append(
                    {
                        "company_name": company,
                        "Location": location,
                        "Phone": phone,
                        "Website": website,
                        "Source": source,
                    }
                )
                progress.progress(i / len(selected))

            status.success("Demo augmentation complete.")
            result_df = pd.DataFrame(rows)
            st.session_state["demo_results"] = result_df

    result_df = st.session_state.get("demo_results")
    if isinstance(result_df, pd.DataFrame) and not result_df.empty:
        st.subheader("Demo results")
        st.dataframe(result_df, use_container_width=True, hide_index=True)

        st.download_button(
            "Download demo results",
            data=dataframe_to_excel_bytes(result_df),
            file_name="demo-augmented-companies.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


with tab_workflow:
    st.subheader("Agent workflow")
    st.markdown(
        """
1. **Read company names** from a CSV file.
2. **Discover likely official websites** using free DDGS search.
3. **Validate the domain** and reject retailers, directories, look-alike sites, and weak regional matches.
4. **Search official-source content** for customer-service phone and location evidence.
5. **Rank phone candidates** so customer-service/customer-care numbers beat warranty, fax, press, or store numbers.
6. **Validate location evidence** using headquarters/corporate-address language.
7. **Return `UNKNOWN` instead of guessing** when evidence is insufficient.
8. **Perform human QA** on the final dataset for difficult edge cases.
        """
    )

    st.subheader("Why human QA remains important")
    st.write(
        "Web search can return regional sites, retailers, stale support numbers, or locations that refer "
        "to stores and distribution centers rather than the company itself. The final project therefore "
        "combines automation with explicit validation rules and manual review."
    )

    st.subheader("Project files")
    st.code(
        """app.py
src/augment_companies.py
data/starter-companies.csv
output/augmented-companies.xlsx
reflection/Aleks_Obuhovskiy_AI_Data_Augmentor_Reflection.pdf
requirements.txt
README.md""",
        language="text",
    )
