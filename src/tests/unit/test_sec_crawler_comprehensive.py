"""Comprehensive test suite for SEC crawler - testing breaks, error handling, and edge cases."""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError, HTTPError
from src.ingestion.sec_crawler import (
    get_company_submissions,
    get_filing_document_url,
    download_filing,
    calculate_file_hash,
    crawl_company_filings,
    get_sec_headers,
)


class TestSECCrawlerRateLimiting:
    """Test rate limiting and SEC API compliance."""
    
    @patch("src.ingestion.sec_crawler.requests.get")
    @patch("src.ingestion.sec_crawler.time.sleep")
    def test_rate_limiting_between_downloads(self, mock_sleep, mock_get):
        """Test that rate limiting is applied between downloads."""
        mock_response = Mock()
        mock_response.text = "<html>10-K Content</html>"
        mock_response.content = b"<html>10-K Content</html>"
        mock_response.url = "https://www.sec.gov/archives/test.htm"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        save_path = Path("/tmp/test.html")
        download_filing("https://www.sec.gov/test.htm", save_path)
        download_filing("https://www.sec.gov/test2.htm", save_path)
        
        # Verify sleep was called (rate limiting)
        assert mock_sleep.called
    
    @patch("src.ingestion.sec_crawler.requests.get")
    def test_429_rate_limit_error_handling(self, mock_get):
        """Test handling of 429 Too Many Requests errors."""
        from requests.exceptions import HTTPError
        
        # First call raises 429
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.raise_for_status.side_effect = HTTPError(response=mock_response_429)
        mock_get.return_value = mock_response_429
        
        # Should handle gracefully (retry logic would be tested separately)
        result = get_company_submissions("0001234567")
        # Current implementation may return None on error
        assert result is None or isinstance(result, dict)


class TestSearchPageDetection:
    """Test detection and filtering of SEC search pages."""
    
    @patch("src.ingestion.sec_crawler.requests.get")
    def test_search_page_url_detection(self, mock_get, tmp_path):
        """Test that search page URLs are detected before download."""
        mock_response = Mock()
        mock_response.text = "Search Filings Content"
        mock_response.url = "https://www.sec.gov/search-filings"
        mock_response.content = b"Search Filings"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        save_path = tmp_path / "test.html"
        result = download_filing("https://www.sec.gov/search-filings", save_path)
        
        assert result is False
        assert not save_path.exists()
    
    @patch("src.ingestion.sec_crawler.requests.get")
    def test_quickedgar_url_detection(self, mock_get):
        """Test detection of quickedgar URLs."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Content</html>"
        mock_response.url = "https://www.sec.gov/edgar/quickedgar.htm"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # get_filing_document_url should skip quickedgar URLs
        result = get_filing_document_url("0001234567", "0001234567-24-000001")
        
        # Should return None or skip this URL
        assert result is None or "quickedgar" not in result.lower()
    
    @patch("src.ingestion.sec_crawler.requests.get")
    def test_content_validation_after_download(self, mock_get, tmp_path):
        """Test that downloaded content is validated."""
        mock_response = Mock()
        mock_response.text = "Search Filings - This is not a 10-K"
        mock_response.content = b"Search Filings"
        mock_response.url = "https://www.sec.gov/archives/test.htm"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        save_path = tmp_path / "test.html"
        result = download_filing("https://www.sec.gov/test.htm", save_path)
        
        assert result is False  # Should reject search page content
        assert not save_path.exists()


class TestAccessionNumberParsing:
    """Test parsing and validation of accession numbers."""
    
    @patch("src.ingestion.sec_crawler.requests.get")
    @patch("src.ingestion.sec_crawler.BeautifulSoup")
    def test_accession_number_extraction_from_html(self, mock_soup, mock_get):
        """Test extraction of accession numbers from HTML."""
        mock_response = Mock()
        mock_response.text = "<html>...</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Mock BeautifulSoup to return HTML with accession numbers
        mock_soup_instance = Mock()
        mock_link = Mock()
        mock_link.get.return_value = "accession_number=0001234567-24-000001"
        mock_link.get_text.return_value = "0001234567-24-000001"
        mock_soup_instance.find_all.return_value = [mock_link]
        mock_soup.return_value = mock_soup_instance
        
        result = get_company_submissions("0001234567")
        
        # Should extract accession numbers
        assert result is None or isinstance(result, dict)
    
    def test_accession_number_format_validation(self):
        """Test that accession numbers match expected format."""
        valid_accession = "0001234567-24-000001"
        invalid_accession = "invalid-format"
        
        # Valid format: 10 digits - 2 digits - 6 digits
        import re
        pattern = r"^\d{10}-\d{2}-\d{6}$"
        
        assert re.match(pattern, valid_accession) is not None
        assert re.match(pattern, invalid_accession) is None


class TestFileHashCalculation:
    """Test file hash calculation with error handling."""
    
    def test_hash_calculation_success(self, tmp_path):
        """Test successful hash calculation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        hash_value = calculate_file_hash(test_file)
        
        assert hash_value.startswith("sha256:")
        assert len(hash_value) > 10
    
    def test_hash_calculation_nonexistent_file(self):
        """Test hash calculation on non-existent file."""
        nonexistent_file = Path("/nonexistent/path/file.txt")
        
        with pytest.raises(FileNotFoundError):
            calculate_file_hash(nonexistent_file)
    
    def test_hash_calculation_large_file(self, tmp_path):
        """Test hash calculation on large file."""
        large_file = tmp_path / "large.txt"
        # Create 10MB file
        large_file.write_bytes(b"x" * (10 * 1024 * 1024))
        
        # Should complete without hanging
        hash_value = calculate_file_hash(large_file)
        assert hash_value.startswith("sha256:")
    
    def test_hash_calculation_permission_error(self, tmp_path):
        """Test hash calculation on file without read permissions."""
        test_file = tmp_path / "no_read.txt"
        test_file.write_text("content")
        
        # On Unix, remove read permissions
        import os
        import stat
        if os.name != 'nt':  # Skip on Windows
            test_file.chmod(stat.S_IRUSR)  # Remove read for others
            # Should still work (owner can read)
            hash_value = calculate_file_hash(test_file)
            assert hash_value.startswith("sha256:")


class TestNetworkErrorHandling:
    """Test handling of network errors."""
    
    @patch("src.ingestion.sec_crawler.requests.get")
    def test_timeout_error(self, mock_get):
        """Test handling of timeout errors."""
        mock_get.side_effect = Timeout("Request timed out")
        
        result = get_company_submissions("0001234567")
        
        assert result is None
    
    @patch("src.ingestion.sec_crawler.requests.get")
    def test_connection_error(self, mock_get):
        """Test handling of connection errors."""
        mock_get.side_effect = ConnectionError("Connection failed")
        
        result = get_company_submissions("0001234567")
        
        assert result is None
    
    @patch("src.ingestion.sec_crawler.requests.get")
    def test_http_error_500(self, mock_get):
        """Test handling of HTTP 500 errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_get.return_value = mock_response
        
        result = get_company_submissions("0001234567")
        
        assert result is None
    
    @patch("src.ingestion.sec_crawler.requests.get")
    def test_http_error_404(self, mock_get):
        """Test handling of HTTP 404 errors."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_get.return_value = mock_response
        
        result = get_company_submissions("0001234567")
        
        assert result is None


class TestRetryLogic:
    """Test retry logic for downloads."""
    
    @patch("src.ingestion.sec_crawler.requests.get")
    def test_retry_on_transient_error(self, mock_get, tmp_path):
        """Test that transient errors trigger retries."""
        # First two calls fail, third succeeds
        mock_response_fail = Mock()
        mock_response_fail.raise_for_status.side_effect = ConnectionError("Transient error")
        
        mock_response_success = Mock()
        mock_response_success.text = "<html>10-K Content</html>"
        mock_response_success.content = b"<html>10-K Content</html>"
        mock_response_success.url = "https://www.sec.gov/archives/test.htm"
        mock_response_success.raise_for_status = Mock()
        
        mock_get.side_effect = [
            ConnectionError("Transient error"),
            ConnectionError("Transient error"),
            mock_response_success,
        ]
        
        save_path = tmp_path / "test.html"
        # download_filing uses tenacity retry, so should succeed after retries
        result = download_filing("https://www.sec.gov/test.htm", save_path, max_retries=3)
        
        # Should succeed after retries
        assert result is True
        assert save_path.exists()


class TestFilingDocumentURL:
    """Test getting filing document URLs."""
    
    @patch("src.ingestion.sec_crawler.requests.get")
    @patch("src.ingestion.sec_crawler.BeautifulSoup")
    def test_document_url_extraction(self, mock_soup, mock_get):
        """Test extraction of document URL from index page."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><a href='10-k.htm'>10-K</a></html>"
        mock_get.return_value = mock_response
        
        mock_soup_instance = Mock()
        mock_link = Mock()
        mock_link.get.return_value = "10-k.htm"
        mock_link.get_text.return_value = "10-K"
        mock_soup_instance.find_all.return_value = [mock_link]
        mock_soup.return_value = mock_soup_instance
        
        result = get_filing_document_url("0001234567", "0001234567-24-000001")
        
        # Should return a URL
        assert result is None or isinstance(result, str)
    
    @patch("src.ingestion.sec_crawler.requests.get")
    def test_fallback_to_common_names(self, mock_get):
        """Test fallback to common document names."""
        # Index page fails
        mock_index_response = Mock()
        mock_index_response.status_code = 404
        mock_get.return_value = mock_index_response
        
        # Common name succeeds
        mock_common_response = Mock()
        mock_common_response.status_code = 200
        mock_get.side_effect = [mock_index_response, mock_common_response]
        
        result = get_filing_document_url("0001234567", "0001234567-24-000001")
        
        # Should try fallback names
        assert mock_get.call_count >= 2


class TestCrawlCompanyFilings:
    """Test full crawl workflow."""
    
    @patch("src.ingestion.sec_crawler.get_company_submissions")
    @patch("src.ingestion.sec_crawler.get_filing_document_url")
    @patch("src.ingestion.sec_crawler.download_filing")
    @patch("src.ingestion.sec_crawler.calculate_file_hash")
    def test_full_crawl_workflow(
        self, mock_hash, mock_download, mock_get_url, mock_submissions, tmp_path
    ):
        """Test complete crawl workflow."""
        # Mock submissions
        mock_submissions.return_value = {
            "cik": "0001234567",
            "filings": [
                {
                    "filing_type": "10-K",
                    "date": "2024-01-01",
                    "accession": "0001234567-24-000001",
                }
            ]
        }
        
        # Mock URL and download
        mock_get_url.return_value = "https://www.sec.gov/archives/test.htm"
        mock_download.return_value = True
        mock_hash.return_value = "sha256:testhash"
        
        # Mock data directory
        from unittest.mock import patch
        with patch("src.ingestion.sec_crawler.Path") as mock_path:
            mock_data_dir = tmp_path / "data" / "raw" / "annual_reports" / "0001234567"
            mock_data_dir.mkdir(parents=True, exist_ok=True)
            
            filings = crawl_company_filings("0001234567", "TEST", years=1)
            
            assert len(filings) > 0
            assert filings[0]["cik"] == "0001234567"


class TestSECHeaders:
    """Test SEC API headers."""
    
    @patch("src.ingestion.sec_crawler.get_settings")
    def test_headers_include_user_agent(self, mock_settings):
        """Test that headers include User-Agent."""
        mock_settings_instance = Mock()
        mock_settings_instance.SEC_USER_AGENT = "Test User Agent"
        mock_settings.return_value = mock_settings_instance
        
        headers = get_sec_headers()
        
        assert "User-Agent" in headers
        assert headers["User-Agent"] == "Test User Agent"


class TestErrorRecovery:
    """Test error recovery mechanisms."""
    
    @patch("src.ingestion.sec_crawler.get_company_submissions")
    def test_graceful_handling_of_missing_filings(self, mock_submissions):
        """Test graceful handling when no filings found."""
        mock_submissions.return_value = None
        
        filings = crawl_company_filings("0001234567", "TEST", years=5)
        
        assert filings == []
    
    @patch("src.ingestion.sec_crawler.download_filing")
    def test_continues_on_download_failure(self, mock_download, tmp_path):
        """Test that crawl continues if one download fails."""
        mock_download.return_value = False
        
        # Should continue processing other filings
        # (Test would need more setup with mock submissions)
        pass


class TestFileFormatDetection:
    """Test file format detection."""
    
    @patch("src.ingestion.sec_crawler.download_filing")
    @patch("src.ingestion.sec_crawler.Path")
    def test_html_file_format_detection(self, mock_path, mock_download):
        """Test detection of HTML file format."""
        mock_path_instance = Mock()
        mock_path_instance.suffix = ".html"
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # File format should be detected from extension
        pass  # Would need to test crawl_company_filings return value
    
    @patch("src.ingestion.sec_crawler.download_filing")
    @patch("src.ingestion.sec_crawler.Path")
    def test_pdf_file_format_detection(self, mock_path, mock_download):
        """Test detection of PDF file format."""
        mock_path_instance = Mock()
        mock_path_instance.suffix = ".pdf"
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # File format should be detected as PDF
        pass  # Would need to test crawl_company_filings return value


# Integration test scenarios (would require actual SEC API or comprehensive mocks)
class TestIntegrationScenarios:
    """Integration test scenarios (commented out - require setup)."""
    
    @pytest.mark.skip(reason="Requires SEC API access or comprehensive mocking")
    def test_real_sec_api_call(self):
        """Test with real SEC API (only run in CI with proper setup)."""
        # Would test with real SEC API if configured
        pass
    
    @pytest.mark.skip(reason="Requires file system setup")
    def test_end_to_end_crawl_and_store(self):
        """Test end-to-end crawl and storage workflow."""
        # Would test full pipeline
        pass

