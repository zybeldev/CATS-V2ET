from uuid import uuid4

from cats.adapters.evidence import PublicEvidenceRequest, PublicWebEvidenceSource


def test_public_evidence_ingestion_strips_markup_and_preserves_provenance():
    source = PublicWebEvidenceSource(
        fetcher=lambda url: "<html><body><h1>Acme Results</h1><p>Revenue increased.</p></body></html>"
    )
    instrument_id = uuid4()
    doc = source.ingest(
        PublicEvidenceRequest(
            url="https://example.test/acme-results",
            source_name="Example Public Filing",
            financial_instrument_id=instrument_id,
        )
    )
    assert "Revenue increased" in doc.text
    assert "<p>" not in doc.text
    assert doc.external_reference == "https://example.test/acme-results"
    assert doc.financial_instrument_id == instrument_id
    assert doc.metadata["source_type"] == "PUBLIC_WEB"


def test_public_evidence_extracts_publication_date_from_structured_metadata():
    source = PublicWebEvidenceSource(
        fetcher=lambda url: '''
        <html><head>
          <meta property="article:published_time" content="2026-09-01T14:30:00Z">
        </head><body><p>Material financial update.</p></body></html>
        '''
    )
    doc = source.ingest(
        PublicEvidenceRequest(
            url="https://example.test/material-update",
            source_name="Example News",
        )
    )

    assert doc.observed_at is not None
    assert doc.observed_at.isoformat() == "2026-09-01T14:30:00+00:00"
    assert doc.metadata["source_date_status"] == "KNOWN"
    assert doc.metadata["source_date_origin"] == "HTML_METADATA"
