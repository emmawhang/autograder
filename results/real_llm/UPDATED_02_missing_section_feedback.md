# GW08 Autograder Feedback

## Score: 15/100

## Rubric Breakdown

- **Attempt and notebook completeness**: 10/10
  - Reason: Submission is non-empty and includes meaningful code toward the Table 3 replication.
- **Data loading**: 10/10
  - Reason: Correctly loads the monthly Goyal-Welch data file and handles separator/decimal formatting if needed.
- **Date parsing and sample filtering**: 5/10
  - Reason: Partially correct date parsing and sample filtering, but missing key aspects.
- **Predictor construction**: 5/15
  - Reason: Only one predictor ('dp') is correctly constructed.
- **Lag handling**: 5/10
  - Reason: Lag handling is partially correct for 'dp', but missing for other predictors and 'infl'.
- **In-sample regression**: 5/10
  - Reason: In-sample regression is run for one predictor ('dp'), but missing for other predictors.
- **In-sample adjusted R2**: 5/10
  - Reason: In-sample adjusted R2 is computed for one predictor ('dp'), but missing for other predictors and using 'rsquared_adj' instead of manual calculation.
- **Out-of-sample rolling procedure**: 0/10
  - Reason: Out-of-sample rolling procedure is completely missing.
- **Historical mean benchmark**: 0/5
  - Reason: Historical mean benchmark is not computed.
- **OOS adjusted R2**: 0/5
  - Reason: OOS adjusted R2 is not computed.
- **Expected sign restriction**: 0/5
  - Reason: Expected sign restriction is not applied.
- **Final Table 3 output**: 5/10
  - Reason: Final table has correct structure, but only one predictor ('dp') and missing OOS_R2_head.

## Final Feedback

The submission is incomplete and missing key aspects of the Table 3 replication, including out-of-sample rolling procedure, historical mean benchmark, and expected sign restriction.

## Flags For Manual Review

- Out-of-sample rolling procedure is completely missing
- Historical mean benchmark is not computed
- Expected sign restriction is not applied
