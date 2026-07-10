from app.models.simulation import SimulationUploadedFile
from app.modules.realtime.retrieval import retrieve_context_chunks


def test_retrieval_prefers_the_uploaded_chunk_matching_the_current_answer():
    record = SimulationUploadedFile(
        simulation_id="simulation-1",
        file_name="brief.txt",
        content_type="text/plain",
        size_bytes=1000,
        upload_status="registered",
        extracted_text=(
            "The opening should establish trust before commercial pressure. "
            "The renewal deadline is 30 September and the internal owner is the CFO."
        ),
        extracted_summary_text="The brief covers trust and renewal timing.",
        extracted_excerpt_text="The renewal deadline is 30 September.",
    )

    chunks = retrieve_context_chunks([record], query_text="What is the renewal deadline?")

    assert chunks
    assert "renewal deadline is 30 september" in chunks[0].lower()
