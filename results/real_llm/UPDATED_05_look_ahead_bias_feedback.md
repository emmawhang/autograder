# GW08 Autograder Feedback

## Score: 0/100

## Rubric Breakdown

- **Attempt and notebook completeness**: 0/10
  - Reason: Submission contains critical errors and does not follow instructions.
- **Data loading**: 5/10
  - Reason: Data is loaded but used incorrectly due to look-ahead bias.
- **Date parsing and sample filtering**: 5/10
  - Reason: Dates are parsed but sample filtering does not prevent look-ahead bias.
- **Predictor construction**: 0/15
  - Reason: Predictors are not correctly constructed to prevent look-ahead bias.
- **Lag handling**: 0/10
  - Reason: Lag handling is incorrect due to the use of future predictor values.
- **In-sample regression**: 0/10
  - Reason: In-sample regression is not correctly implemented due to look-ahead bias.
- **In-sample adjusted R2**: 0/10
  - Reason: In-sample adjusted R2 calculation is not relevant due to critical errors.
- **Out-of-sample rolling procedure**: 0/10
  - Reason: OOS rolling procedure contains look-ahead bias.
- **Historical mean benchmark**: 0/5
  - Reason: Historical mean benchmark is not correctly used due to look-ahead bias.
- **OOS adjusted R2**: 0/5
  - Reason: OOS adjusted R2 calculation is not relevant due to critical errors.
- **Expected sign restriction**: 0/5
  - Reason: Expected sign restriction is not correctly applied due to look-ahead bias.
- **Final Table 3 output**: 0/10
  - Reason: Final table output is incorrect due to look-ahead bias and other critical errors.

## Final Feedback

The submission contains critical errors, most notably look-ahead bias, which severely impacts the validity of the results. It is essential to revisit the implementation, ensuring that only past data is used for predictions and that the methodology aligns with the instructions provided.

## Flags For Manual Review

- Look-ahead bias in predictor usage
- Incorrect implementation of out-of-sample rolling procedure
