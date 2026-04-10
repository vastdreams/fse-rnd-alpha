# Literature Review Memo: Operating Efficiency, Profitability, and Operating Leverage

**Study**: P&L Efficiency Alpha  
**Date**: February 27, 2026  
**Author**: Abhishek Sehgal

---

## Purpose

This memo synthesizes the key academic literature supporting the P&L Efficiency Alpha research design. It covers three interconnected strands: (1) the profitability anomaly in asset pricing, (2) operating leverage and cost-structure risk, and (3) DuPont-style financial ratio analysis for return prediction.

---

## 1. The Profitability Anomaly

### Core Finding
Firms with higher profitability earn higher subsequent stock returns, contradicting the intuition that profitable firms are "safer" and should earn lower expected returns.

### Key Papers

**Novy-Marx (2013)** — *The Other Side of Value: The Gross Profitability Premium*  
The landmark paper in this literature. Shows that gross profitability (GP/A = (Revenue − CoGS) / Assets) is a powerful cross-sectional return predictor. Key results:
- GP/A has roughly the same power as B/M in predicting returns, but with opposite sign
- GP/A subsumes much of the HML value premium
- Profitable firms outperform by 0.31%/month in the full sample
- The result is robust to size, value, momentum, and investment controls

**Relevance to our study**: We decompose GP/A further. Our gross efficiency (1 − CoGS/Revenue) captures the numerator of GP/A but uses revenue rather than assets as the denominator, and we add SG&A, operating income, and net income layers.

**Fama & French (2006)** — *Profitability, Investment and Average Returns*  
Establishes that expected profitability predicts cross-sectional returns in a valuation framework (Gordon model rearranged). High expected profitability → higher expected returns, controlling for investment and B/M.

**Fama & French (2015)** — *A Five-Factor Asset Pricing Model*  
Formalizes the profitability finding by adding RMW (Robust Minus Weak operating profitability) and CMA (Conservative Minus Aggressive investment) to the three-factor model. RMW is constructed from operating profitability = (Revenue − CoGS − SG&A − Interest) / Book Equity.

**Relevance**: Our PNL efficiency composite must demonstrate alpha *after* controlling for RMW. If the composite merely replicates RMW, there is no incremental contribution. The sector-relative normalization and four-component decomposition are the mechanisms by which we expect to find incremental information.

**Ball, Gerakos, Linnainmaa & Nikolaev (2015)** — *Deflating Profitability*  
Shows that profitability scaled by assets introduces noise through the deflator. Cash-based profitability and non-deflated profitability measures outperform standard GP/A. This supports our choice to scale by revenue rather than assets.

**Ball, Gerakos, Linnainmaa & Nikolaev (2016)** — *Accruals, Cash Flows, and Operating Profitability*  
Decomposes profitability into cash and accrual components. The cash component drives return predictability. Our four ratios are inherently closer to cash-based (they use actual reported line items, not accrual adjustments), though profit conversion includes non-cash items.

**Haugen & Baker (1996)** — *Commonality in the Determinants of Expected Stock Returns*  
Early evidence that profitability (among many financial ratios) predicts returns. Documents that the market's cross-sectional return predictors are persistent over time.

**Asness, Frazzini & Pedersen (2019)** — *Quality Minus Junk*  
Constructs a comprehensive quality factor combining profitability, growth, safety, and payout. Shows a significant QMJ premium globally. Our PNL efficiency composite can be viewed as a focused sub-factor within the quality framework, isolating the cost-structure dimension.

### Summary of the Profitability Strand
The literature overwhelmingly supports a positive relationship between profitability and returns. Our contribution is to decompose this aggregate into specific cost channels and test which layers of the income statement carry the return-predictive power. The sector-relative approach adds a novel dimension by removing industry-level effects.

---

## 2. Operating Leverage and Cost Structure Risk

### Core Insight
Firms with high fixed costs (high operating leverage) experience larger profit swings for a given revenue change, creating systematic risk that is compensated with a return premium.

### Key Papers

**Lev (1974)** — *On the Association between Operating Leverage and Risk*  
Theoretical and empirical link between the degree of operating leverage (DOL = % change in EBIT / % change in sales) and beta. Higher DOL → higher systematic risk.

**Mandelker & Rhee (1984)** — *Impact of Operating and Financial Leverage on Systematic Risk*  
Extends Lev (1974) to jointly estimate operating and financial leverage effects on beta. Finds both contribute independently to systematic risk.

**Novy-Marx (2011)** — *Operating Leverage*  
Modern empirical treatment. Shows that firms with high CoGS/Assets (high variable costs, low operating leverage) earn lower returns. Interprets the profitability premium partly through the lens of operating leverage: profitable firms earn more because they have higher fixed costs → more operating leverage → more risk → higher expected returns.

**Relevance**: Our gross efficiency measure (1 − CoGS/Revenue) is closely related to the operating leverage proxy in Novy-Marx (2011). However, we add three more layers (SG&A, operating income, profit conversion) and normalize within sectors, which Novy-Marx does not.

**Anderson, Banker & Janakiraman (2003)** — *Are SGA Costs Sticky?*  
Documents that SG&A costs rise by about 0.55% for a 1% revenue increase but fall by only 0.35% for a 1% revenue decrease. This asymmetry creates persistent differences in overhead efficiency across firms that are not quickly arbitraged away.

**Banker & Byzalov (2014)** — *Asymmetric Cost Behavior*  
Confirms and extends the cost-stickiness finding, showing it is robust across industries and time periods. The persistence of cost asymmetry supports our hypothesis that overhead efficiency contains durable return-predictive information.

**Garcia & Norli (2012)** — *Geographic Dispersion and Stock Returns*  
While focused on geographic dispersion, documents that cost-structure characteristics (including operating leverage proxies) vary with firm geography and create return differentials.

### Summary of the Operating Leverage Strand
Operating leverage creates risk premiums. Our decomposition captures multiple channels through which cost structure affects profit sensitivity: CoGS (direct production leverage), SG&A (overhead leverage), and the interaction of these through operating and net income. The stickiness of SG&A suggests that overhead efficiency is a particularly durable signal.

---

## 3. DuPont Decomposition and Ratio Analysis

### Core Insight
Disaggregating profitability into margin, turnover, and leverage components improves forecasting of both future earnings and stock returns.

### Key Papers

**Soliman (2008)** — *The Use of DuPont Analysis by Market Participants*  
Shows that changes in DuPont components (profit margin and asset turnover) predict future earnings and abnormal returns. Analysts who decompose ROE make better forecasts. Importantly, the market does not fully incorporate the information in the decomposition, creating a mispricing opportunity.

**Relevance**: Directly supports our approach. If the market underreacts to DuPont-style decomposition, it should also underreact to our more granular P&L decomposition. Soliman's finding that the *margin* component is particularly informative motivates our focus on margin-related efficiency ratios.

**Fairfield & Yohn (2001)** — *Using Asset Turnover and Profit Margin to Forecast Changes in Profitability*  
Demonstrates that profit margin and asset turnover changes provide independent information about future profitability changes. High-margin firms with improving margins have the most persistent profitability.

**Nissim & Penman (2001)** — *Ratio Analysis and Equity Valuation*  
Comprehensive framework for using financial ratios in valuation. Shows that operating profit margin, asset turnover, and leverage ratios have distinct forecasting properties for residual income. The paper establishes that individual ratio components contain information lost in aggregation.

**Ou & Penman (1989)** — *Financial Statement Analysis and the Prediction of Stock Returns*  
Pioneering work showing that a composite of financial statement ratios predicts stock returns. The composite captures information not in current earnings, suggesting the market does not fully process financial statement data.

### Summary of the Ratio Analysis Strand
The DuPont and ratio analysis literature strongly supports the principle that disaggregated financial metrics contain return-predictive information that aggregate measures miss. Our four-component P&L decomposition extends this principle to a more granular cost-structure analysis.

---

## Search Criteria and Methodology

### Search Strategy
- Google Scholar, SSRN, JSTOR searches for: "gross profitability premium," "operating leverage returns," "cost structure asset pricing," "DuPont analysis returns," "SGA cost stickiness returns," "profitability anomaly"
- Citation chaining from Novy-Marx (2013), Fama-French (2015), Soliman (2008)
- Cross-reference with existing R&D Alpha bibliography to identify shared foundations

### Inclusion Criteria
- Published in peer-reviewed journals or established working paper series (NBER, SSRN with >50 downloads)
- Directly relevant to profitability, cost structure, operating leverage, or financial ratio analysis
- Contains empirical results on cross-sectional return prediction or asset pricing

### Excluded
- Pure theoretical models without empirical application
- Non-U.S. studies without clear generalizability argument
- Studies focused exclusively on earnings management/accruals anomaly (related but distinct)
- Practitioner articles without rigorous methodology

### Download Provenance
All cited papers were verified against publisher DOI pages. PDFs where available are stored in `paper_references/pnl_efficiency/`. BibTeX entries were validated against Crossref metadata.
