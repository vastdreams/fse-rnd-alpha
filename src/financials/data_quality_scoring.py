"""Data quality scoring system for financial data."""
from typing import Dict, Any, Optional
from src.models.orm.financials_core import FinancialsCore
from src.financials.validation import calculate_data_quality_score, validate_financials_core
from src.logging.logger import get_logger

logger = get_logger(__name__)


class DataQualityScorer:
    """
    Comprehensive data quality scoring system.
    
    Scores data based on:
    - Completeness
    - Consistency
    - Accuracy indicators
    - Reasonableness checks
    """
    
    def __init__(self):
        """Initialize quality scorer."""
        self.scoring_weights = {
            "completeness": 0.4,
            "consistency": 0.3,
            "accuracy": 0.2,
            "reasonableness": 0.1,
        }
    
    def score_financial_data(self, financials: FinancialsCore) -> Dict[str, Any]:
        """
        Calculate comprehensive quality score for financial data.
        
        Args:
            financials: FinancialsCore object to score
            
        Returns:
            Dictionary with quality scores and details
        """
        # Get base validation results
        quality_result = calculate_data_quality_score(financials)
        validation_result = validate_financials_core(financials)
        
        # Calculate accuracy score (based on data source and validation)
        accuracy_score = self._calculate_accuracy_score(financials, validation_result)
        
        # Calculate reasonableness score
        reasonableness_score = self._calculate_reasonableness_score(financials)
        
        # Weighted overall score
        overall_score = (
            quality_result["completeness_score"] * self.scoring_weights["completeness"] +
            quality_result["consistency_score"] * self.scoring_weights["consistency"] +
            accuracy_score * self.scoring_weights["accuracy"] +
            reasonableness_score * self.scoring_weights["reasonableness"]
        )
        
        return {
            "overall_score": overall_score,
            "completeness_score": quality_result["completeness_score"],
            "consistency_score": quality_result["consistency_score"],
            "accuracy_score": accuracy_score,
            "reasonableness_score": reasonableness_score,
            "validation": validation_result,
            "quality_grade": self._get_quality_grade(overall_score),
            "recommendations": self._get_recommendations(quality_result, validation_result),
        }
    
    def _calculate_accuracy_score(
        self,
        financials: FinancialsCore,
        validation_result: Dict[str, Any]
    ) -> float:
        """
        Calculate accuracy score based on validation results.
        
        Args:
            financials: Financial data
            validation_result: Validation results
            
        Returns:
            Accuracy score (0.0 to 1.0)
        """
        score = 1.0
        
        # Errors reduce accuracy significantly
        if validation_result.get("errors"):
            score -= len(validation_result["errors"]) * 0.2
        
        # Warnings reduce accuracy slightly
        if validation_result.get("warnings"):
            score -= len(validation_result["warnings"]) * 0.05
        
        return max(0.0, score)
    
    def _calculate_reasonableness_score(self, financials: FinancialsCore) -> float:
        """
        Calculate reasonableness score based on data values.
        
        Args:
            financials: Financial data
            
        Returns:
            Reasonableness score (0.0 to 1.0)
        """
        score = 1.0
        issues = 0
        
        # Check for extreme values
        if financials.revenue and financials.revenue < 0:
            issues += 1
        
        if financials.net_income:
            # Check if net income is extremely large relative to revenue
            if financials.revenue and financials.revenue > 0:
                net_margin = abs(financials.net_income) / financials.revenue
                if net_margin > 1.0:  # Net income > revenue (unusual)
                    issues += 1
        
        if financials.total_assets and financials.total_assets < 0:
            issues += 1
        
        # Check R&D expense reasonableness
        if financials.rd_expense and financials.revenue and financials.revenue > 0:
            rd_intensity = financials.rd_expense / financials.revenue
            if rd_intensity > 0.5:  # R&D > 50% of revenue (very unusual)
                issues += 0.5  # Less severe
        
        # Reduce score based on issues
        score -= issues * 0.1
        
        return max(0.0, score)
    
    def _get_quality_grade(self, score: float) -> str:
        """
        Get quality grade letter (A-F) based on score.
        
        Args:
            score: Quality score (0.0 to 1.0)
            
        Returns:
            Quality grade letter
        """
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"
    
    def _get_recommendations(
        self,
        quality_result: Dict[str, Any],
        validation_result: Dict[str, Any]
    ) -> List[str]:
        """
        Get recommendations for improving data quality.
        
        Args:
            quality_result: Quality scoring results
            validation_result: Validation results
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Completeness recommendations
        missing_fields = quality_result.get("missing_fields", [])
        if missing_fields:
            recommendations.append(
                f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        # Consistency recommendations
        if validation_result.get("errors"):
            recommendations.append(
                f"Fix {len(validation_result['errors'])} data consistency errors"
            )
        
        if validation_result.get("warnings"):
            recommendations.append(
                f"Review {len(validation_result['warnings'])} data quality warnings"
            )
        
        # Completeness recommendations
        if quality_result.get("completeness_score", 1.0) < 0.8:
            recommendations.append(
                "Improve data completeness - add missing financial fields"
            )
        
        return recommendations


# Global scorer instance
_scorer_instance: Optional[DataQualityScorer] = None


def get_quality_scorer() -> DataQualityScorer:
    """Get global quality scorer instance."""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = DataQualityScorer()
    return _scorer_instance


def score_financial_data_quality(financials: FinancialsCore) -> Dict[str, Any]:
    """
    Convenience function to score financial data quality.
    
    Args:
        financials: FinancialsCore object
        
    Returns:
        Quality score dictionary
    """
    scorer = get_quality_scorer()
    return scorer.score_financial_data(financials)

