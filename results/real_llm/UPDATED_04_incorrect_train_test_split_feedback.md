# GW08 Autograder Feedback

## Score: 0/100

## Rubric Breakdown

- **Attempt and notebook completeness**: 0/10
  - Reason: Submission does not follow the required structure and does not include meaningful code toward the Table 3 replication.
- **Data loading**: 0/10
  - Reason: Data loading is incorrect, does not match the original assignment.
- **Date parsing and sample filtering**: 0/10
  - Reason: Date parsing and sample filtering are not correctly implemented.
- **Predictor construction**: 0/15
  - Reason: Predictor construction is incomplete and does not match the original assignment.
- **Lag handling**: 0/10
  - Reason: Lag handling is not correctly implemented.
- **In-sample regression**: 0/10
  - Reason: In-sample regression is not correctly implemented.
- **In-sample adjusted R2**: 0/10
  - Reason: In-sample adjusted R2 calculation is incorrect.
- **Out-of-sample rolling procedure**: 0/10
  - Reason: Out-of-sample rolling procedure is not correctly implemented, uses a much shorter OOS window and includes future data.
- **Historical mean benchmark**: 0/5
  - Reason: Historical mean benchmark is not correctly implemented, uses future data.
- **OOS adjusted R2**: 0/5
  - Reason: OOS adjusted R2 calculation is incorrect.
- **Expected sign restriction**: 0/5
  - Reason: Expected sign restriction is not correctly implemented.
- **Final Table 3 output**: 0/10
  - Reason: Final table output is incomplete and does not match the required structure.

## Final Feedback

The submission does not follow the required structure and does not include meaningful code toward the Table 3 replication. The data loading, date parsing, and sample filtering are not correctly implemented. The predictor construction, lag handling, in-sample regression, and out-of-sample rolling procedure are also incorrect. The historical mean benchmark and OOS adjusted R2 calculations are not correctly implemented. The expected sign restriction is not correctly applied. The final table output is incomplete and does not match the required structure.

## Flags For Manual Review

- Look-ahead bias in out-of-sample rolling procedure
- Incorrect historical mean benchmark calculation
- Incorrect OOS adjusted R2 calculation
