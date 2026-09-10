# GW08 Autograder — Possible Errors, Edge Cases & False Positives

## False Positives (marks correct work as wrong)

### 1. Variable Name Aliasing
**Issue**: Student uses semantically correct but different variable names.
- `epremium` instead of `equity_premium`
- `market_return` instead of `CRSP_SPvw`
- `dividend_price` instead of `dp`
- `log_price_ratio` instead of `log(Index)`

**Risk**: LLM may penalize predictor construction / data naming even if logic is correct.
**Evidence**: Test 03 scored 20/100 for this reason; LLM didn't recognize `dp_index` as `dp`.

**Mitigation**: Either (a) explicitly list acceptable aliases in rubric, or (b) relax the variable-name penalty and focus on output correctness.

---

### 2. Equivalent but Differently-Expressed Formulas
**Issue**: Multiple mathematically equivalent ways to compute the same thing.
- `log(D12) - log(Index)` vs `log(D12/Index)` for dp
- `(1 - r2) * (T - k) / (T - 1)` vs `(T - k) / (T - 1) * (1 - r2)` for adjusted R2
- `OLS(y, add_constant(x))` vs `OLS(y, X)` where X already has a constant

**Risk**: LLM might flag as "wrong predictor construction" when formulas are equivalent.
**Evidence**: Test 04 uses simple division; reference uses log difference—LLM reported 0/15 for predictors.

**Mitigation**: In rubric, clarify that equivalent formulas are acceptable; focus on final output match.

---

### 3. Different but Valid Sample Periods
**Issue**: Student uses slightly different date ranges or cutoffs.
- Start date '1927-12-01' vs '1927-11-01' (one month off)
- End date '2005-12-31' vs '2005-12-01'
- Start date '1937-05-01' for csp instead of reference date

**Risk**: LLM penalizes for "wrong sample filtering" even if the choice is reasonable.
**Evidence**: Test 04 uses common dates but LLM scored 0/10 for date parsing due to other issues.

**Mitigation**: Document accepted date ranges in rubric; allow ±1 month tolerance if justified.

---

### 4. OOS Window Implementation Variants
**Issue**: Strict 240-month rolling vs expanding window vs 20-year blocks all have merit.
- Student uses 240-month rolling: correct per reference
- Student uses expanding window (start to t): simpler, but biased
- Student uses 20-year blocks: different but clearer

**Risk**: LLM may penalize non-240-month windows as "incorrect OOS procedure" even if defensible.
**Evidence**: Test 04 scored 0/10 for OOS procedure; test 07 scored 0/10 despite having rolling code.

**Mitigation**: Explicitly state 240-month rolling in rubric; if you accept alternatives, list them.

---

### 5. Floating Point Precision Mismatches
**Issue**: Results differ by 0.01–0.1% due to rounding or numerical precision.
- IS_R2_head = 5.43 vs 5.44
- OOS_R2_head = -2.10 vs -2.09

**Risk**: LLM may report "incorrect OOS R2 calculation" if exact match not found in code review.
**Evidence**: Rubric says "small numerical differences are acceptable," but LLM may still flag.

**Mitigation**: Provide tolerance range (±0.5%) in rubric; add explicit note about rounding.

---

## False Negatives (marks wrong work as correct)

### 1. Subtle Look-Ahead Bias
**Issue**: Leakage is hard to detect without running code.
- Off-by-one indexing errors: `iloc[pos+1]` used correctly for target but incorrectly for features
- Rolling regressor that includes current-month predictor in training but should be lagged
- Mean calculation includes future data by accident

**Risk**: LLM catches gross violations but misses subtle offset errors.
**Evidence**: Test 05 scored 0/100 (correctly caught), but code patterns like `pred = reg.predict(x_future)` might pass if x_future looks reasonable in isolation.

**Mitigation**: Add a specific rubric check: "Forecasting loop must use only past data; predict target using predictors from ≤ lag month."

---

### 2. Wrong Benchmark Masquerading as Mean
**Issue**: Benchmark that's numerically close to historical mean but conceptually wrong.
- Rolling mean (mean of training window) vs historical mean (mean of full past)
- Median (close to mean in normal distributions)
- Trimmed mean (0.1% tails removed)

**Risk**: LLM may accept if the description "benchmark" or "mean" appears in code text.
**Evidence**: Test 06 scored 10/100 and was flagged for median; this worked as intended. But a rolling mean might slip through.

**Mitigation**: Require explicit `mean(full_history)` or `iloc[start_pos:pos+1].mean()` pattern; flag rolling mean separately.

---

### 3. Sign Restriction Applied at Wrong Time
**Issue**: Correct concept but wrong execution order.
- Apply sign restriction after one-step forecast instead of before
- Apply to predicted value instead of regression coefficient
- Apply after adjusting R2 instead of before

**Risk**: LLM may see keywords "sign restriction" and "expected_sign" and award partial credit even if logic is wrong.
**Evidence**: Test "medium_wrong" (test 02 variant) scored 60/100 despite multiple sign-restriction errors.

**Mitigation**: Add rubric detail: "Sign restriction must be applied to regression coefficient before using it for prediction."

---

### 4. Missing Data / NaN Handling
**Issue**: Code doesn't explicitly handle or report missing values.
- Uses `.fillna(0)` silently, biasing results
- Drops rows without announcing, changing sample size
- Produces NaN in final table but doesn't flag it

**Risk**: LLM may not catch unless NaN appears in final output or a warning is missing.
**Evidence**: None of our test cases have NaN in final output, so hard to judge.

**Mitigation**: Require students to report data completeness (e.g., "X% of data available after lagging"). LLM can then flag if completeness is low.

---

### 5. Incorrect Adjusted R2 Formula
**Issue**: Student uses plain R2 or wrong adjustment.
- Computes `r2 + (1-r2)*(T-k)/(T-1)` (adds instead of subtracts)
- Uses wrong k value (e.g., k=1 instead of k=2)
- Forgets adjustment entirely, reports plain `reg.rsquared`

**Risk**: If the final output numbers are close, LLM may not catch the formula error.
**Evidence**: Test 02 (medium_wrong) uses k=1 incorrectly; scored 60/100. LLM noted the mistake but gave credit anyway.

**Mitigation**: Require code snippet showing the adjustment formula explicitly; LLM can pattern-match `(T - k) / (T - 1)`.

---

## Edge Cases (unexpected behavior)

### 1. Notebook Doesn't Run
**Issue**: Code has no syntax errors but fails at runtime.
- Missing import: `import numpy as np` forgotten
- File not found: `data/GW05_original_monthly.csv` doesn't exist
- Memory error: OOS loop builds huge array
- Infinite loop: off-by-one in range()

**Risk**: LLM sees notebook text but can't execute; may miss runtime errors or award points for non-functional code.
**Evidence**: Test 09 has syntax error (unmatched paren); LLM scored 0/100 (correct). But a runtime error might be treated differently.

**Mitigation**: Optionally add a pre-check: execute notebook in isolated kernel and capture stderr. Attach runtime errors to flags_for_manual_review.

---

### 2. Huge Notebook / Context Overflow
**Issue**: Student adds lots of exploratory code, plots, or debugging output.
- 50+ cells of visualization
- 1000+ lines of intermediate results
- Large embedded data arrays

**Risk**: LLM context window fills up; may truncate feedback or miss key sections.
**Evidence**: Not seen in our test cases, but possible if students copy entire reference notebook and add notes.

**Mitigation**: Set a reasonable notebook-size limit (e.g., <100 cells, <10,000 lines); warn students in template.

---

### 3. Empty or Malformed Output DataFrame
**Issue**: `df_results` exists but is incorrect in subtle ways.
- Correct column names but transposed (predictors in columns, not rows)
- Correct shape but NaN for all values
- Wrong data type (strings "95.4" instead of float 95.4)
- Missing rows for some predictors

**Risk**: LLM may award "Final Table 3 output" points even if table is barely usable.
**Evidence**: Test 10 has empty table; scored low (0/10). But a partially-filled table might get credit.

**Mitigation**: Require exact structure check: 15 rows (one per predictor), 2 columns (IS_R2_head, OOS_R2_head), all numeric.

---

### 4. Duplicate Variable Names / Shadowing
**Issue**: Student redefines variables accidentally.
- `dp` computed twice with different logic
- `equity_premium` reassigned mid-notebook
- Function `compute_monthly_stats` called but then redefined

**Risk**: LLM sees both definitions; may credit incorrect version if it appears later in code text.
**Evidence**: Not tested, but possible if student iterates and forgets to clean up.

**Mitigation**: In template, warn students against redefining key variables. In rubric, note that first correct definition is the one that counts.

---

### 5. Date Parsing Edge Cases
**Issue**: yyyymm format has boundary conditions.
- Input '202013' (year 2020, month 13) — invalid
- Input '192701' (year 1927, month 01) — valid but unusual
- Leap year handling: Feb 28/29 inconsistencies

**Risk**: LLM may not catch invalid dates if code doesn't raise an exception.
**Evidence**: Not seen in tests, but possible if student manually constructs dates.

**Mitigation**: Data file is fixed; no risk if loaded correctly. If students input dates, validate range in rubric check.

---

### 6. Off-by-One Errors in Indexing
**Issue**: Python 0-indexing vs date/month semantics.
- `iloc[pos]` vs `iloc[pos+1]` confusion in rolling loop
- `.shift(1)` vs `.shift(2)` incorrect for specific predictors
- `range(start_pos + 240, end_pos)` should be `range(start_pos + 240, end_pos + 1)` or vice versa

**Risk**: Hard for LLM to catch without tracing through loop logic step-by-step.
**Evidence**: None of our tests have clean off-by-one; would require careful manual inspection.

**Mitigation**: In rubric, specify exact indexing semantics (e.g., "for loop runs from month 240 to month N inclusive; use predictors from months 0 to month-1").

---

### 7. Numerical Instability
**Issue**: Large or small numbers cause numerical issues.
- Equity premium in decimals (0.01) vs percents (1.0) — OOS R2 can become negative or >1
- Divide-by-zero: if MSE_mean = 0, OOS R2 undefined
- Extreme outliers in residuals inflate MSE

**Risk**: LLM may not catch if final numbers "look reasonable" (e.g., -10% OOS R2 is valid in finance but unusual).
**Evidence**: Reference solution has negative OOS R2 for some predictors; acceptable per paper.

**Mitigation**: Document in rubric: "OOS R2 can be negative; this is acceptable. Report as given."

---

## LLM-Specific Risks

### 1. Hallucinations
**Issue**: LLM generates feedback about code it didn't see or misinterprets.
- Claims "sign restriction applied incorrectly" when it's not in code
- Praises "excellent data handling" for minimal work
- Invents missing criteria not in rubric

**Risk**: Feedback confuses students; scores don't match actual code.
**Mitigation**: Spot-check JSON + markdown feedback against student code manually. Set `temperature=0` (done).

---

### 2. Consistency Across Runs
**Issue**: Same notebook graded twice produces different scores.
- First run: 95/100. Second run: 85/100.
- Feedback text changes.

**Risk**: Students appeal inconsistent scores.
**Mitigation**: Save all JSON outputs; log model + API used. Use fixed seed/temperature (done).

---

### 3. Context Length Limits
**Issue**: Notebook + rubric + prompts exceed LLM token limit.
- Groq/OpenAI imposes max tokens
- Autograder silently truncates input, missing key sections

**Risk**: Incomplete grading without error signal.
**Mitigation**: Monitor token usage in autograder. Set a notebook cell count or size limit.

---

### 4. Rubric Interpretation Drift
**Issue**: LLM interprets rubric criteria differently than intended.
- "Partial credit for correct methodology" → LLM gives 50% if method is conceptually right but numbers are wrong
- "Penalize look-ahead bias" → LLM zeros out entire submission instead of subtracting 10 points

**Risk**: Grading severity varies unpredictably.
**Mitigation**: Include examples in rubric (e.g., "Example: if OOS R2 formula is wrong but predictors are correct, award 5/10 for this criterion, not 0/10").

---

## Summary Table: Risk Levels

| Issue | Severity | Likelihood | Evidence |
|-------|----------|------------|----------|
| Variable name aliasing | Medium | High | Test 03 (20/100) |
| Subtle look-ahead bias | High | Medium | Test 05 caught it |
| Wrong benchmark (rolling vs fixed mean) | High | Medium | Test 06 flagged; others might not |
| Sign restriction at wrong time | Medium | Medium | Test 02 (60/100) |
| Off-by-one indexing | High | Low | Not tested |
| LLM hallucinations | Medium | Low | Spot checks OK so far |
| OOS window variant acceptance | Medium | High | Tests 04, 07 unclear |
| Floating-point precision | Low | Medium | Rubric allows tolerance |
| Notebook too large / timeout | Low | Low | Not seen in tests |
| Invalid date handling | Low | Low | Data file validated |

---

## Recommended Mitigations (Priority)

**High Priority:**
1. Clarify OOS window requirement (240 months strict, rolling, past-only) in rubric prompt.
2. Add explicit "no leakage" criterion to rubric; LLM should pattern-match for index/lag correctness.
3. List acceptable variable-name aliases OR enforce canonical names in autograder pre-check.
4. Require adjusted R2 formula snippet in code; pattern-match for correct formula.

**Medium Priority:**
5. Add spot-check: execute notebook and capture runtime errors; attach to flags.
6. Document sign-restriction timing explicitly with example code.
7. Benchmark comparison must show historical-mean pattern in code text.

**Low Priority:**
8. Add notebook size/cell limits to template warnings.
9. Include numerical tolerance (±0.5%) in rubric examples.
10. Maintain execution logs for consistency audits.
