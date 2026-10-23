from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from class_quality.pipeline import assess_file
from class_quality.schemas import AssessmentResult


load_dotenv()
st.set_page_config(page_title="Class quality assessor", page_icon="📚", layout="wide")


def render_result(result: AssessmentResult) -> None:
    st.subheader(f"Assessment: {result.label}")
    left, middle, provider_column, right = st.columns(4)
    left.metric("VTT-only score", f"{result.overall_score:.0f}/100")
    middle.metric("Evidence confidence", f"{result.confidence * 100:.0f}%")
    provider_column.metric("Evidence provider", result.provider)
    right.metric("Grounded observations", len(result.evidence))
    st.caption(result.coverage_note)
    if result.provider_note:
        st.info(result.provider_note)

    st.markdown("#### Dimension scores")
    columns = st.columns(len(result.dimensions))
    for column, dimension in zip(columns, result.dimensions):
        column.metric(dimension.display_name, f"{dimension.score:.0f}/100")
        column.caption(dimension.rationale)

    st.markdown("#### Evidence used")
    for event in result.evidence:
        st.markdown(
            f"**{event.dimension.replace('_', ' ').title()} · "
            f"{event.start_sec / 60:.1f}–{event.end_sec / 60:.1f} min**  \n"
            f"{event.observation}  \n"
            f"> {event.evidence_quote}"
        )

    if result.caveats:
        st.markdown("#### Limits of this result")
        for caveat in result.caveats:
            st.warning(caveat)


st.title("Class quality assessor")
st.write("Transcript-led assessment with traceable evidence. Local Ollama is used by default.")
st.info("External processing is disabled unless ALLOW_EXTERNAL_PROCESSING=true is explicitly set in .env.")

upload = st.file_uploader("Upload a WebVTT transcript", type=["vtt"])
if upload:
    if st.button("Assess class", type="primary"):
        with tempfile.TemporaryDirectory(prefix="humaniti_") as temp_dir:
            upload_path = Path(temp_dir) / Path(upload.name).name
            upload_path.write_bytes(upload.getbuffer())
            with st.spinner("Reading transcript and extracting grounded observations…"):
                try:
                    result = assess_file(upload_path)
                except Exception as error:  # Streamlit needs a clear user-facing failure.
                    st.error(f"Assessment could not run: {error}")
                else:
                    render_result(result)

st.divider()
st.caption("The label is a prototype rubric result, not a trained-model prediction. VTT cannot assess visual or audio quality.")
