from __future__ import annotations

from ..services import DataService


def render() -> None:
    import streamlit as st

    service = DataService()
    collections = service.document_manager.list_collections()
    collection_names = [item["name"] for item in collections]
    selected_collection = st.selectbox("Collection", collection_names)

    documents = service.list_documents(selected_collection)
    st.title("Data Browser")
    st.caption("Browse ingested documents and chunk-level metadata")
    st.table(documents)

    if not documents:
        st.info("No documents available for the selected collection.")
        return

    doc_map = {f'{item["title"]} :: {item["doc_id"]}': item for item in documents}
    selected_label = st.selectbox("Document", list(doc_map.keys()))
    selected_doc = doc_map[selected_label]
    detail = service.get_document_detail(selected_doc["doc_id"], selected_collection)

    st.subheader(detail["title"])
    st.write({
        "source": detail["source"],
        "doc_type": detail["doc_type"],
        "chunk_count": detail["chunk_count"],
        "image_count": detail["image_count"],
    })
    st.json(detail["metadata"])

    for chunk in detail["chunks"]:
        with st.expander(f'Chunk {chunk["chunk_index"]}: {chunk["chunk_id"]}', expanded=False):
            st.write(chunk["content"])
            st.json(chunk["metadata"])
            if chunk["image_refs"]:
                st.write({"image_refs": chunk["image_refs"]})
