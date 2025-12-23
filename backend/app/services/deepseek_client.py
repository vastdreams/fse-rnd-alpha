"""
PATH: backend/app/services/deepseek_client.py
PURPOSE:
  - DeepSeek API client for AI-powered R&D analysis
  - Uses DeepSeek 3.2 model for concurrent analysis
  
API: https://api.deepseek.com
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# DeepSeek V3.2 Speciale - thinking mode with 128K output
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v3.2_speciale_expires_on_20251215"


@dataclass
class AnalysisResult:
    """Result from AI analysis."""
    symbol: str
    analysis_type: str
    content: Dict[str, Any]
    confidence: float
    model: str


class DeepSeekClient:
    """
    Async client for DeepSeek API with concurrent analysis support.
    Uses DeepSeek V3.2 Speciale (thinking mode) model.
    """
    
    def __init__(self, api_key: str, max_concurrent: int = 10):
        self.api_key = api_key
        self.max_concurrent = max_concurrent
        self.model = "deepseek-reasoner"  # DeepSeek V3.2 Speciale thinking mode
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def _chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """Make a chat completion request."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        async with self.semaphore:
            try:
                async with self.session.post(
                    f"{DEEPSEEK_BASE_URL}/chat/completions",
                    json=payload,
                    timeout=60
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error = await response.text()
                        logger.error(f"DeepSeek API error {response.status}: {error}")
                        return None
            except Exception as e:
                logger.error(f"DeepSeek request failed: {e}")
                return None
    
    async def analyze_rd_profile(self, company_data: Dict[str, Any]) -> AnalysisResult:
        """
        Analyze a company's R&D profile using AI.
        
        Args:
            company_data: Dict with symbol, name, sector, rd_by_year, financials
        """
        symbol = company_data.get("symbol", "UNKNOWN")
        
        prompt = f"""Analyze the R&D investment profile for {symbol} ({company_data.get('name', '')}).

Company Data:
- Sector: {company_data.get('sector', 'N/A')}
- Average R&D Intensity: {company_data.get('avg_rd_intensity', 0):.2f}%
- Total R&D Spend: ${company_data.get('total_rd_spend', 0)/1e9:.1f}B
- Years of Data: {company_data.get('years_with_rd', 0)}

R&D History (recent 5 years):
{self._format_rd_history(company_data.get('rd_by_year', [])[:5])}

Provide a structured analysis with:
1. R&D Investment Category (High/Medium/Low intensity)
2. Trend Analysis (Increasing/Stable/Decreasing)
3. Competitive Position Assessment
4. Key Insights (2-3 bullet points)
5. Research Potential Score (1-10)

Format as JSON with keys: category, trend, competitive_position, insights, research_score"""

        messages = [
            {"role": "system", "content": "You are a quantitative financial analyst specializing in R&D factor analysis for academic research. Provide concise, data-driven insights in JSON format."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self._chat_completion(messages)
        
        if response:
            try:
                import json
                # Try to extract JSON from response
                content = self._extract_json(response)
                return AnalysisResult(
                    symbol=symbol,
                    analysis_type="rd_profile",
                    content=content,
                    confidence=0.85,
                    model=self.model
                )
            except:
                return AnalysisResult(
                    symbol=symbol,
                    analysis_type="rd_profile",
                    content={"raw_analysis": response},
                    confidence=0.7,
                    model=self.model
                )
        
        return AnalysisResult(
            symbol=symbol,
            analysis_type="rd_profile",
            content={"error": "Analysis failed"},
            confidence=0.0,
            model=self.model
        )
    
    async def analyze_sector_rd_efficiency(self, sector_data: List[Dict]) -> Dict[str, Any]:
        """Analyze R&D efficiency across a sector."""
        
        prompt = f"""Analyze R&D efficiency for companies in this sector data:

{self._format_sector_data(sector_data)}

Provide:
1. Sector R&D efficiency ranking
2. Key patterns in R&D investment
3. Outliers and their characteristics
4. Recommendations for research cohort selection
5. Hypothesis suggestions for R&D impact study

Format as JSON."""

        messages = [
            {"role": "system", "content": "You are a quantitative researcher analyzing R&D investment patterns for academic publication. Be precise and cite specific data points."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self._chat_completion(messages, max_tokens=3000)
        
        if response:
            return self._extract_json(response)
        return {"error": "Analysis failed"}
    
    async def generate_research_insights(
        self, 
        rd_trends: List[Dict],
        sector_comparison: List[Dict],
        top_performers: List[Dict]
    ) -> Dict[str, Any]:
        """Generate research insights for publication."""
        
        prompt = f"""Based on this R&D factor analysis data, generate insights for academic research:

## R&D TRENDS (Last 20 Years)
{self._format_trends(rd_trends)}

## SECTOR COMPARISON
{self._format_sector_comparison(sector_comparison)}

## TOP R&D PERFORMERS
{self._format_top_performers(top_performers)}

Generate:
1. Executive Summary (2-3 sentences)
2. Key Findings (5 bullet points)
3. Statistical Observations
4. Hypothesis Validation Suggestions
5. Recommended Next Steps for Research
6. Potential Publication Angles

Format as JSON with clear structure."""

        messages = [
            {"role": "system", "content": "You are a senior quantitative finance researcher preparing insights for a peer-reviewed publication on R&D investment and shareholder returns. Be rigorous and academic in tone."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self._chat_completion(messages, max_tokens=4000, temperature=0.2)
        
        if response:
            return self._extract_json(response)
        return {"error": "Analysis failed"}
    
    async def batch_analyze_companies(
        self, 
        companies: List[Dict[str, Any]]
    ) -> List[AnalysisResult]:
        """
        Concurrently analyze multiple companies.
        
        Args:
            companies: List of company data dicts
            
        Returns:
            List of AnalysisResult objects
        """
        tasks = [self.analyze_rd_profile(c) for c in companies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        return [r for r in results if isinstance(r, AnalysisResult)]
    
    def _format_rd_history(self, rd_data: List[Dict]) -> str:
        """Format R&D history for prompt."""
        if not rd_data:
            return "No R&D data available"
        
        lines = []
        for item in rd_data:
            year = item.get('year', 'N/A')
            rd = item.get('rd_expense', 0) or 0
            intensity = item.get('rd_intensity', 0) or 0
            lines.append(f"  - {year}: ${rd/1e9:.2f}B ({intensity:.1f}% intensity)")
        return "\n".join(lines)
    
    def _format_sector_data(self, data: List[Dict]) -> str:
        """Format sector data for prompt."""
        lines = []
        for item in data[:10]:
            lines.append(f"- {item.get('symbol', 'N/A')}: {item.get('avg_rd_intensity', 0):.1f}% avg intensity, ${item.get('total_rd_spend', 0)/1e9:.1f}B total")
        return "\n".join(lines)
    
    def _format_trends(self, trends: List[Dict]) -> str:
        """Format trend data for prompt."""
        lines = []
        for t in trends[-10:]:
            lines.append(f"- {t.get('year', 'N/A')}: {t.get('avg_rd_intensity', 0):.2f}% avg, {t.get('companies', 0)} companies")
        return "\n".join(lines)
    
    def _format_sector_comparison(self, sectors: List[Dict]) -> str:
        """Format sector comparison for prompt."""
        lines = []
        for s in sectors[:8]:
            lines.append(f"- {s.get('sector', 'N/A')}: {s.get('avg_rd_intensity', 0):.2f}% intensity, {s.get('company_count', 0)} companies")
        return "\n".join(lines)
    
    def _format_top_performers(self, performers: List[Dict]) -> str:
        """Format top performers for prompt."""
        lines = []
        for p in performers[:10]:
            lines.append(f"- {p.get('symbol', 'N/A')} ({p.get('sector', 'N/A')}): {p.get('avg_rd_intensity', 0):.1f}%")
        return "\n".join(lines)
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from response text."""
        import json
        import re
        
        # Try direct parse
        try:
            return json.loads(text)
        except:
            pass
        
        # Try to find JSON block
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # Try to find any JSON-like structure
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass
        
        return {"raw_response": text}

