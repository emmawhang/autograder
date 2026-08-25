# GW08 Autograder Feedback

## Score: 20/100

## Rubric Breakdown

- **Attempt and notebook completeness**: 5/10
  - Reason: Submission is incomplete and lacks meaningful code toward the Table 3 replication.
- **Data loading**: 10/10
  - Reason: Correctly loads the monthly Goyal-Welch data file.
- **Date parsing and sample filtering**: 5/10
  - Reason: Partially correct date parsing and sample filtering, but lacks proper handling.
- **Predictor construction**: 0/15
  - Reason: Incorrectly constructs key predictors, using different variable names and formulas.
- **Lag handling**: 0/10
  - Reason: Fails to apply correct lagging to predictors, including inflation.
- **In-sample regression**: 0/10
  - Reason: Does not run OLS regressions of equity premium on lagged predictors for each variable.
- **In-sample adjusted R2**: 0/10
  - Reason: Incorrectly computes IS_R2_head, using wrong formula and not reporting in percent.
- **Out-of-sample rolling procedure**: 0/10
  - Reason: Fails to implement strict 20-year rolling window and uses incorrect forecasting procedure.
- **Historical mean benchmark**: 0/5
  - Reason: Does not correctly compare model forecast errors against historical mean forecast errors.
- **OOS adjusted R2**: 0/5
  - Reason: Incorrectly computes OOS_R2_head, using wrong formula and not reporting in percent.
- **Expected sign restriction**: 0/5
  - Reason: Fails to apply sign restriction correctly, if at all.
- **Final Table 3 output**: 0/10
  - Reason: Does not produce dataframe with predictor names as rows and exactly two columns: IS_R2_head and OOS_R2_head.

## Final Feedback

The submission lacks completeness and contains significant errors in predictor construction, lag handling, and regression analysis. It fails to implement the out-of-sample rolling procedure and historical mean benchmark correctly. The final output does not meet the required format.

## Flags For Manual Review

- Inconsistent variable naming
- Lack of proper lag handling
- Incorrect implementation of out-of-sample rolling procedure
