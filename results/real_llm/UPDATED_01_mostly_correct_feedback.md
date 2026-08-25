# GW08 Autograder Feedback

## Score: 95/100

## Rubric Breakdown

- **Attempt and notebook completeness**: 10/10
  - Reason: The submission is non-empty and includes meaningful code toward the Table 3 replication.
- **Data loading**: 10/10
  - Reason: The student correctly loads the monthly Goyal-Welch data file and handles separator/decimal formatting if needed.
- **Date parsing and sample filtering**: 10/10
  - Reason: The student correctly converts yyyymm to dates, sets a date index, and uses the intended sample periods.
- **Predictor construction**: 15/15
  - Reason: The student correctly constructs key predictors such as dp, dy, ep, de, e10p, tms, and dfy.
- **Lag handling**: 10/10
  - Reason: The student uses lagged predictors correctly in regression: .shift(1) for most; .shift(2) for 'infl'.
- **In-sample regression**: 10/10
  - Reason: The student runs OLS regressions of equity premium on lagged predictors for each variable.
- **In-sample adjusted R2**: 10/10
  - Reason: The student correctly computes IS_R2_head = R² - (1-R²)*(T-k)/(T-1) and reports in percent.
- **Out-of-sample rolling procedure**: 10/10
  - Reason: The student implements strict 20-year (240-month) rolling window: for each month t, fit model only on data available up to that month.
- **Historical mean benchmark**: 5/5
  - Reason: The student correctly compares model forecast errors against historical mean forecast errors.
- **OOS adjusted R2**: 5/5
  - Reason: The student correctly computes OOS_R2_head = 1 - (MSE_model / MSE_mean), then adjusts: R² - (1-R²)*(T-k)/(T-1), in percent.
- **Expected sign restriction**: 0/5
  - Reason: The student does not apply the expected sign restriction correctly.
- **Final Table 3 output**: 10/10
  - Reason: The student produces a dataframe with predictor names as rows (index) and exactly two columns: IS_R2_head, OOS_R2_head.

## Final Feedback

The student's submission is mostly correct, but the expected sign restriction is not applied. The student should review the implementation of the expected sign restriction.

## Flags For Manual Review

- None
