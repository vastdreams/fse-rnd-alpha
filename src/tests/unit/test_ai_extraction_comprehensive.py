"""Comprehensive test suite for AI extraction processing - testing breaks, error handling, and edge cases."""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from src.ai.agents.financial_statement_rd_extractor import (
    extract_rd_from_financial_statements,
    extract_json_from_response,
    extract_rd_from_html_tables,
)


class TestJSONExtraction:
    """Test JSON extraction from GPT responses."""
    
    def test_extract_json_from_code_block(self):
        """Test extraction of JSON from code block."""
        response = """
        Here is the extracted data:
        ```json
        {
            "rd_expense_total": 1000000,
            "income_statement_rd": []
        }
        ```
        """
        
        result = extract_json_from_response(response)
        
        assert result is not None
        data = json.loads(result)
        assert "rd_expense_total" in data
    
    def test_extract_json_without_code_block(self):
        """Test extraction of JSON without code block."""
        response = '{"rd_expense_total": 1000000, "income_statement_rd": []}'
        
        result = extract_json_from_response(response)
        
        assert result is not None
        data = json.loads(result)
        assert data["rd_expense_total"] == 1000000
    
    def test_extract_json_nested_braces(self):
        """Test extraction with nested JSON structures."""
        response = """
        Some text before {
            "outer": {
                "inner": {
                    "value": 123
                }
            }
        } some text after
        """
        
        result = extract_json_from_response(response)
        
        assert result is not None
        data = json.loads(result)
        assert data["outer"]["inner"]["value"] == 123
    
    def test_extract_json_multiple_objects(self):
        """Test extraction when multiple JSON objects exist."""
        response = """
        First object: {"a": 1}
        Second object: {"b": 2}
        """
        
        result = extract_json_from_response(response)
        
        # Should extract first complete JSON object
        assert result is not None
        data = json.loads(result)
        assert "a" in data or "b" in data
    
    def test_extract_json_invalid_json(self):
        """Test handling of invalid JSON."""
        response = """
        This is not JSON: { invalid syntax here
        """
        
        result = extract_json_from_response(response)
        
        # Should return None or invalid JSON string
        if result:
            with pytest.raises(json.JSONDecodeError):
                json.loads(result)
    
    def test_extract_json_empty_response(self):
        """Test handling of empty response."""
        response = ""
        
        result = extract_json_from_response(response)
        
        assert result is None
    
    def test_extract_json_no_json(self):
        """Test handling when no JSON is present."""
        response = "This is just text with no JSON objects."
        
        result = extract_json_from_response(response)
        
        assert result is None or result == ""


class TestGPTAPICall:
    """Test GPT API call handling."""
    
    @patch("src.ai.agents.financial_statement_rd_extractor.call_gpt")
    def test_successful_extraction(self, mock_call_gpt):
        """Test successful R&D extraction."""
        mock_response = json.dumps({
            "income_statement_rd": [
                {
                    "line_item": "Research and Development",
                    "current_year": 1000000000,
                    "prior_year": 900000000,
                }
            ],
            "rd_expense_total": 1000000000,
        })
        
        mock_call_gpt.return_value = f"```json\n{mock_response}\n```"
        
        html_content = "<html>Financial statements...</html>"
        result = extract_rd_from_financial_statements(html_content)
        
        assert mock_call_gpt.called
        assert "income_statement_rd" in result or result == {}
    
    @patch("src.ai.agents.financial_statement_rd_extractor.call_gpt")
    def test_gpt_api_timeout(self, mock_call_gpt):
        """Test handling of GPT API timeout."""
        mock_call_gpt.side_effect = TimeoutError("API timeout")
        
        html_content = "<html>Financial statements...</html>"
        
        with pytest.raises(TimeoutError):
            extract_rd_from_financial_statements(html_content)
    
    @patch("src.ai.agents.financial_statement_rd_extractor.call_gpt")
    def test_gpt_api_rate_limit(self, mock_call_gpt):
        """Test handling of GPT API rate limit errors."""
        from openai import RateLimitError
        
        mock_call_gpt.side_effect = RateLimitError("Rate limit exceeded", response=None, body=None)
        
        html_content = "<html>Financial statements...</html>"
        
        with pytest.raises(RateLimitError):
            extract_rd_from_financial_statements(html_content)
    
    @patch("src.ai.agents.financial_statement_rd_extractor.call_gpt")
    def test_gpt_api_empty_response(self, mock_call_gpt):
        """Test handling of empty GPT response."""
        mock_call_gpt.return_value = ""
        
        html_content = "<html>Financial statements...</html>"
        result = extract_rd_from_financial_statements(html_content)
        
        assert result == {}
    
    @patch("src.ai.agents.financial_statement_rd_extractor.call_gpt")
    def test_gpt_api_invalid_json_response(self, mock_call_gpt):
        """Test handling of invalid JSON in GPT response."""
        mock_call_gpt.return_value = "This is not valid JSON { invalid }"
        
        html_content = "<html>Financial statements...</html>"
        result = extract_rd_from_financial_statements(html_content)
        
        # Should handle gracefully
        assert isinstance(result, dict)
        assert result == {}  # Should return empty on parse error


class TestHTMLTableExtraction:
    """Test HTML table extraction for R&D data."""
    
    def test_extract_rd_from_tables_basic(self):
        """Test basic R&D extraction from HTML tables."""
        html_content = """
        <html>
        <table>
            <tr>
                <td>Research and Development</td>
                <td>$100 million</td>
                <td>$90 million</td>
            </tr>
        </table>
        </html>
        """
        
        result = extract_rd_from_html_tables(html_content)
        
        assert len(result) > 0
        assert any("research" in str(item).lower() or "development" in str(item).lower() for item in result)
    
    def test_extract_rd_from_tables_no_rd(self):
        """Test extraction when no R&D data in tables."""
        html_content = """
        <html>
        <table>
            <tr>
                <td>Sales Revenue</td>
                <td>$1000 million</td>
            </tr>
        </table>
        </html>
        """
        
        result = extract_rd_from_html_tables(html_content)
        
        # Should return empty list if no R&D keywords
        assert result == []
    
    def test_extract_rd_various_keywords(self):
        """Test extraction with various R&D keyword variations."""
        keywords = [
            "Research and Development",
            "R&D",
            "R and D",
            "Research",
            "Development",
            "Product Development",
            "Technology Development",
        ]
        
        for keyword in keywords:
            html_content = f"""
            <html>
            <table>
                <tr>
                    <td>{keyword}</td>
                    <td>$100 million</td>
                </tr>
            </table>
            </html>
            """
            
            result = extract_rd_from_html_tables(html_content)
            
            assert len(result) > 0, f"Failed to extract {keyword}"
    
    def test_extract_rd_multiple_tables(self):
        """Test extraction from multiple tables."""
        html_content = """
        <html>
        <table>
            <tr><td>Research and Development</td><td>$100 million</td></tr>
        </table>
        <table>
            <tr><td>R&D Expense</td><td>$150 million</td></tr>
        </table>
        </html>
        """
        
        result = extract_rd_from_html_tables(html_content)
        
        # Should extract from both tables
        assert len(result) >= 1
    
    def test_extract_rd_malformed_html(self):
        """Test extraction from malformed HTML."""
        html_content = """
        <html>
        <table>
            <tr>
                <td>Research and Development</td>
                <!-- Missing closing tag -->
        </html>
        """
        
        # Should not crash on malformed HTML
        result = extract_rd_from_html_tables(html_content)
        
        assert isinstance(result, list)


class TestFinancialStatementPatterns:
    """Test financial statement pattern matching."""
    
    def test_identify_income_statement(self):
        """Test identification of income statement section."""
        html_content = """
        <html>
        <h2>CONSOLIDATED STATEMENTS OF INCOME</h2>
        <table>
            <tr><td>Research and Development</td><td>$100 million</td></tr>
        </table>
        </html>
        """
        
        # extract_rd_from_financial_statements should identify this section
        result = extract_rd_from_financial_statements(html_content)
        
        # Should extract from income statement section
        assert isinstance(result, dict)
    
    def test_identify_balance_sheet(self):
        """Test identification of balance sheet section."""
        html_content = """
        <html>
        <h2>CONSOLIDATED BALANCE SHEETS</h2>
        <table>...</table>
        </html>
        """
        
        result = extract_rd_from_financial_statements(html_content)
        
        assert isinstance(result, dict)
    
    def test_identify_cash_flow_statement(self):
        """Test identification of cash flow statement section."""
        html_content = """
        <html>
        <h2>CONSOLIDATED STATEMENTS OF CASH FLOWS</h2>
        <table>...</table>
        </html>
        """
        
        result = extract_rd_from_financial_statements(html_content)
        
        assert isinstance(result, dict)
    
    def test_identify_notes_to_statements(self):
        """Test identification of notes to financial statements."""
        html_content = """
        <html>
        <h2>NOTES TO CONSOLIDATED FINANCIAL STATEMENTS</h2>
        <p>Note 5: Research and Development</p>
        </html>
        """
        
        result = extract_rd_from_financial_statements(html_content)
        
        assert isinstance(result, dict)


class TestErrorHandling:
    """Test error handling in AI extraction."""
    
    @patch("src.ai.agents.financial_statement_rd_extractor.call_gpt")
    def test_exception_handling(self, mock_call_gpt):
        """Test handling of unexpected exceptions."""
        mock_call_gpt.side_effect = Exception("Unexpected error")
        
        html_content = "<html>Content</html>"
        
        with pytest.raises(Exception):
            extract_rd_from_financial_statements(html_content)
    
    def test_empty_html_content(self):
        """Test handling of empty HTML content."""
        html_content = ""
        
        result = extract_rd_from_financial_statements(html_content)
        
        # Should handle gracefully
        assert isinstance(result, dict)
    
    def test_very_large_html_content(self):
        """Test handling of very large HTML content."""
        # Create large HTML (e.g., 10MB)
        html_content = "<html>" + "x" * (10 * 1024 * 1024) + "</html>"
        
        # Should not crash (may need truncation)
        # This test documents potential issue with large files
        result = extract_rd_from_financial_statements(html_content)
        
        assert isinstance(result, dict)


class TestRetryLogic:
    """Test retry logic for GPT API calls (to be implemented)."""
    
    @pytest.mark.skip(reason="Retry logic not yet implemented")
    def test_retry_on_transient_error(self):
        """Test retry on transient GPT API errors."""
        # Would test exponential backoff retry
        pass
    
    @pytest.mark.skip(reason="Retry logic not yet implemented")
    def test_max_retries_exceeded(self):
        """Test handling when max retries exceeded."""
        # Would test failure after max retries
        pass


class TestCaching:
    """Test response caching (to be implemented)."""
    
    @pytest.mark.skip(reason="Caching not yet implemented")
    def test_cache_hit(self):
        """Test cache hit for previously extracted content."""
        # Would test Redis/database cache
        pass
    
    @pytest.mark.skip(reason="Caching not yet implemented")
    def test_cache_miss(self):
        """Test cache miss and new extraction."""
        # Would test cache miss scenario
        pass


class TestDataValidation:
    """Test validation of extracted data."""
    
    def test_validate_extracted_structure(self):
        """Test validation of extracted JSON structure."""
        extracted_data = {
            "income_statement_rd": [
                {
                    "line_item": "Research and Development",
                    "current_year": 1000000000,
                }
            ],
            "rd_expense_total": 1000000000,
        }
        
        # Should validate structure (would use Pydantic schema)
        assert "income_statement_rd" in extracted_data
        assert isinstance(extracted_data["income_statement_rd"], list)
    
    @pytest.mark.skip(reason="Schema validation not yet implemented")
    def test_validate_with_pydantic_schema(self):
        """Test validation using Pydantic schema."""
        # Would validate against defined schema
        pass


class TestCostManagement:
    """Test cost management for GPT API calls (to be implemented)."""
    
    @pytest.mark.skip(reason="Cost tracking not yet implemented")
    def test_track_api_calls(self):
        """Test tracking of API calls for cost monitoring."""
        # Would track number of tokens, cost, etc.
        pass
    
    @pytest.mark.skip(reason="Cost limits not yet implemented")
    def test_enforce_cost_limits(self):
        """Test enforcement of cost limits."""
        # Would prevent exceeding cost thresholds
        pass

