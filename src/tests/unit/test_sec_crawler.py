"""Unit tests for SEC crawler."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from src.ingestion.sec_crawler import (
    get_company_submissions,
    get_filing_document_url,
    download_filing,
    calculate_file_hash,
)


@patch("src.ingestion.sec_crawler.requests.get")
def test_get_company_submissions_success(mock_get):
    """Test successful company submissions retrieval."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "filings": {
            "recent": {
                "form": ["10-K", "10-Q"],
                "filingDate": ["2024-01-01", "2023-01-01"],
                "accessionNumber": ["0001234567-24-000001", "0001234567-23-000001"],
            }
        }
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    result = get_company_submissions("0001234567")
    
    assert result is not None
    assert "filings" in result


@patch("src.ingestion.sec_crawler.requests.get")
def test_get_company_submissions_failure(mock_get):
    """Test handling of failed submissions retrieval."""
    mock_get.side_effect = Exception("Network error")
    
    result = get_company_submissions("0001234567")
    
    assert result is None


def test_calculate_file_hash(tmp_path):
    """Test file hash calculation."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    hash_value = calculate_file_hash(test_file)
    
    assert hash_value.startswith("sha256:")
    assert len(hash_value) > 10


@patch("src.ingestion.sec_crawler.requests.get")
def test_download_filing_success(mock_get, tmp_path):
    """Test successful file download."""
    mock_response = Mock()
    mock_response.text = "<html>10-K Annual Report Content</html>"
    mock_response.content = b"<html>10-K Annual Report Content</html>"
    mock_response.url = "https://www.sec.gov/Archives/edgar/data/123/0001234567/test.htm"
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    save_path = tmp_path / "test.html"
    result = download_filing("https://www.sec.gov/test.htm", save_path)
    
    assert result is True
    assert save_path.exists()


@patch("src.ingestion.sec_crawler.requests.get")
def test_download_filing_search_page_redirect(mock_get, tmp_path):
    """Test detection of search page redirect."""
    mock_response = Mock()
    mock_response.text = "Search Filings"
    mock_response.url = "https://www.sec.gov/search-filings"
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    save_path = tmp_path / "test.html"
    result = download_filing("https://www.sec.gov/test.htm", save_path)
    
    assert result is False
    assert not save_path.exists()

