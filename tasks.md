1. Implement fetching the ask prices for arb calculation
To implement the true arbitrage logic, we need the ask prices (yes_ask, no_ask from Kalshi; bestAsk from Polymarket allows deriving both Yes/No asks) in addition to the bid prices. Our current normalization only includes bid prices. enhance the normalization process (_process_... methods) and the normalized structure to include ask prices to enable the more accurate arbitrage logic

2. Finding 'equivalent' events across Kalshi and Polymarket
a) Combined Matching Strategy (e.g., Fuzzy Title + Expiration Time) using the current normalized data?
Market Matching Strategies:
- fuzzy match between subtitles

3. Expiration time matching
- compare expiration times of the markets

4. Category/Tag matching
- compare categories of the markets

TODO:
Semantic Matching (Advanced): Use sentence embeddings (e.g., via sentence-transformers). Convert titles/questions into vectors. Calculate cosine similarity between vectors. Matches are pairs with high cosine similarity (e.g., > 0.9). Best for understanding semantic equivalence even with different phrasing, but computationally more intensive.
Pros: Much more likely to find real matches based on the market's meaning.
Cons: Requires careful text normalization. Fuzzy/semantic methods require tuning (thresholds) and can have false positives/negatives.

Expiration Time Matching:
How: Compare kalshi_market['raw_market']['expiration_time'] (or close_time) with polymarket_market['raw_market']['endDate'].
Implementation: Parse both timestamps into comparable objects (e.g., Python datetime). Match markets where expiration times are identical or very close (within a tolerance like +/- 1 hour or +/- 1 day).
Pros: Uses an objective, structured data point.
Cons: Not sufficient on its own. Many unrelated markets might expire simultaneously. Best used as a secondary filter to confirm potential matches found via Title/Question matching.
Category/Tag Matching:
How: Compare kalshi_market['raw_market']['category'] (often from the parent event) with Polymarket tags (if available in the /events market summaries or by fetching /events/{id}).
Pros: Can help narrow the search space.
Cons: Categories can be broad or inconsistent. Unlikely to be sufficient alone. Best as an optional filtering step.
Recommended Matching Approach:

A Combined Strategy is likely best:

Primary Match: Use Title/Question Matching. Start with Fuzzy Matching due to its balance of simplicity and robustness. If results are poor, consider investing in Semantic Matching. Generate candidate pairs that exceed the similarity threshold.
Secondary Filter: For each candidate pair from step 1, check if their Expiration Times are within a reasonable tolerance (e.g., same day). This helps eliminate pairs that are clearly different events despite similar titles.
Match Confirmation: Pairs passing both steps are considered "equivalent" markets.
