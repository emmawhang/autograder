# Quick Start Guide for Instructors

## Overview
Your GW08 Table 3 autograder has been enhanced with specific grading rules and a validated rubric. This guide shows you how to use the student template, grade submissions, and interpret results.

---

## 1. Distributing to Students

### Student Template
**File to distribute:** `notebooks/templates/GW08_table3_two_cols_student_template.ipynb`

**What students see:**
- 5 numbered tasks with clear requirements
- TODO placeholders where they write code
- Required variable names that the autograder checks
- Expected output format

**Student instructions:**
Students complete 5 tasks:
1. **Setup** — Load and parse data
2. **Construct Predictors** — Create lagged regressors
3. **In-Sample Regressions** — Run OLS for each predictor
4. **Compute Table 3** — Calculate IS/OOS adjusted R²
5. **Write-up** — Interpret results

---

## 2. Running the Autograder

### Quick Command
```bash
source .venv/bin/activate
python app/autograder.py \
  --assignment notebooks/reference/GW08_table3_two_cols.ipynb \
  --submission student_submission.ipynb \
  --rubric config/rubric_gw.txt
```

### Output Files
- **JSON**: Structured scores and reasoning (for records/appeals)
- **Markdown**: Human-readable feedback for students

### Example
```bash
python app/autograder.py \
  --assignment notebooks/reference/GW08_table3_two_cols.ipynb \
  --submission student_a_submission.ipynb \
  --rubric config/rubric_gw.txt \
  --json-out results/student_a_grading.json \
  --md-out results/student_a_feedback.md
```

---

## 3. Understanding Grading

### 9 Critical Rules Applied

The autograder checks for:

1. **Look-ahead bias** — Using future data to predict the past (❌ instant 0/10)
2. **OOS window** — Must be exactly 240 months (❌ wrong size = 0/10)
3. **Adjusted R²** — Correct formula with - not + operator (❌ wrong formula = 0/10)
4. **Benchmark** — Historical mean only, not rolling/median (❌ wrong benchmark = 0/5)
5. **Variables** — Names can vary if logic is correct (✅ aliases accepted)
6. **Lagging** — .shift(1) most predictors, .shift(2) for inflation (⚠️ wrong lag = penalty)
7. **Signs** — Sign restrictions applied to coefficients before prediction
8. **Table format** — Rows=predictors, Columns=IS_R2_head & OOS_R2_head (❌ wrong format = 0/10)
9. **Tolerance** — ±0.5% numerical accuracy accepted (✅ minor rounding OK)

### Rubric Breakdown (100 points)

| Criterion | Points | What's Graded |
|-----------|--------|--------------|
| Attempt & Completeness | 10 | Did they try? All sections attempted? |
| Data Loading | 10 | Correct data file, format handling? |
| Date Parsing | 10 | Correct date conversion and sample period? |
| Predictors | 15 | Correct predictor construction? |
| Lagging | 10 | Correct .shift() usage? |
| In-Sample Regression | 10 | OLS fit correctly? |
| IS Adjusted R² | 10 | Correct formula with - operator? |
| OOS Procedure | 10 | 240-month rolling window? No leakage? |
| Benchmark | 5 | Historical mean only? |
| OOS Adjusted R² | 5 | Correct formula? |
| Sign Restrictions | 5 | Applied correctly? |
| Final Table | 10 | Correct shape, values, labels? |

---

## 4. Reading Grading Output

### JSON Structure
```json
{
  "total_score": 95,
  "max_score": 100,
  "breakdown": [
    {
      "criterion": "Attempt and notebook completeness",
      "score": 10,
      "max_score": 10,
      "reason": "Submission is non-empty with meaningful code..."
    },
    ...
  ]
}
```

**How to interpret:**
- `total_score`: Final grade out of 100
- `breakdown`: Detailed scoring for each of 12 criteria
- `reason`: LLM explanation of the score

### Markdown Feedback
Human-readable summary of:
- Strengths (what the student did well)
- Areas for improvement
- Specific errors detected
- Next steps for revision

---

## 5. Expected Score Ranges

### Full Credit (90-100/100)
✅ Mostly correct submissions with minor issues
- Correct OOS procedure (240-month window)
- Correct formulas (IS & OOS R² with proper adjustment)
- Proper lagging (.shift(1) most, .shift(2) inflation)
- No look-ahead bias

### Partial Credit (40-80/100)
⚠️ Conceptually sound but with significant errors
- Wrong OOS window size (but tried the concept)
- Incomplete sections (e.g., missing some predictors)
- Wrong benchmark method (e.g., median instead of mean)
- Formatting issues in final table

### Failing (0-30/100)
❌ Critical errors or non-functional code
- Look-ahead bias (uses future data)
- Wrong R² formula (missing adjustment)
- Code doesn't run (syntax errors)
- Incomplete implementation (no code, only comments)

### No Credit (0/100)
- Syntax errors (code doesn't run)
- Critical data leakage (look-ahead bias)
- Formula errors caught by LLM

---

## 6. Common Student Mistakes (Auto-Detected)

### Mistake → Grade Impact

| Mistake | Detection | Score |
|---------|-----------|-------|
| Uses median benchmark instead of mean | 🚩 Detected | -5 points |
| OOS window too short (60 months) | 🚩 Detected | 0/10 OOS criterion |
| Adjusted R² formula uses + instead of - | 🚩 Detected | 0/10 R² criterion |
| Uses future data in prediction | 🚩 Detected | 0/100 (critical) |
| Forgets .shift() for lagging | 🚩 Detected | 0/10 lagging criterion |
| Variable names don't match template | ✅ Ignored if logic correct | No penalty |
| Reports 0.05 instead of 5.0 (percent) | 🚩 Detected | 0/10 reporting criterion |
| Code has syntax error | 🚩 Detected | ~0-20/100 |
| Missing OOS procedure entirely | 🚩 Detected | ~15-30/100 |

---

## 7. Troubleshooting

### Issue: "API rate limit reached"
**Cause:** Groq free tier has 100K tokens/day limit
**Solution:** 
- Wait 24 hours for limit to reset, OR
- Upgrade to paid tier at https://console.groq.com/settings/billing

### Issue: "Submission doesn't exist"
**Cause:** Wrong file path
**Solution:** Use absolute path to student notebook, e.g., `/full/path/to/student.ipynb`

### Issue: "JSON parsing error"
**Cause:** LLM response malformed
**Solution:** 
- Check API key in `.env`
- Try the submission again (may be temporary LLM issue)

### Issue: "Fairness concern — student appeals score"
**Solution:**
1. Check JSON output for detailed reasoning
2. Review markdown feedback for specific errors
3. Look at rubric criteria — all 12 are explicit
4. If disagree with LLM: manually grade or adjust rubric for future runs

---

## 8. Monitoring & Improvements

### Check for Issues
After grading a batch:
1. Look for unexpected 0/100 scores (may indicate look-ahead bias)
2. Check if similar students got very different scores (inconsistency)
3. Review markdown feedback for common complaints
4. If fairness concerns arise, check JSON reasoning

### Updating the Rubric
If you want to adjust grading:
1. Edit `config/rubric_gw.txt` (JSON format)
2. Update the description field with your changes
3. Re-grade submissions with `python app/autograder.py ...`

### Providing Student Feedback
Use markdown output: `UPDATED_student_name_feedback.md`
- Share with student for learning
- Can paste directly into LMS feedback system
- Specific, actionable suggestions included

---

## 9. File Organization

```
autograder/
├── autograder.py                              ← Main grading script
├── config/rubric_gw.txt                              ← Scoring rubric (JSON)
├── notebooks/reference/GW08_table3_two_cols.ipynb                 ← Reference solution
├── notebooks/templates/GW08_table3_two_cols_student_template.ipynb ← DISTRIBUTE THIS
├── GW05_original_monthly.csv                  ← Required data
├── tests/submissions/                          ← Test cases (for validation)
│   ├── 01_mostly_correct.ipynb
│   ├── 02_missing_section.ipynb
│   └── ... (8 more test cases)
├── results/real_llm/                          ← Grading outputs
│   ├── student_a_grading.json
│   ├── student_a_feedback.md
│   └── ... (more results)
├── PROJECT_COMPLETION_SUMMARY.md              ← Full project report
├── AUTOGRADER_ENHANCEMENT_REPORT.md           ← Before/after analysis
├── EDGE_CASES_AND_FALSE_POSITIVES.md          ← Risk documentation
└── QUICKSTART_FOR_INSTRUCTORS.md              ← This file
```

---

## 10. Need Help?

### Common Questions

**Q: Can I grade multiple students at once?**
A: No, run autograder once per submission. Use a bash loop for batch grading:
```bash
for notebook in submissions/*.ipynb; do
  python app/autograder.py --assignment notebooks/reference/GW08_table3_two_cols.ipynb --submission "$notebook" --rubric config/rubric_gw.txt
done
```

**Q: What if a student uses a different OOS method?**
A: The rubric strictly requires 240-month rolling window per assignment specs. Different methods will score low on the OOS criterion (0-5/10 depending on reasonableness).

**Q: Can I weight criteria differently?**
A: Yes, edit `config/rubric_gw.txt` and change the `points` field for each criterion. Total must equal 100.

**Q: Should I show students the rubric?**
A: Yes! Transparency helps. Show them the 9 CRITICAL RULES so they understand exactly what's graded.

**Q: What if the autograder makes a mistake?**
A: Check the JSON output for reasoning. If you disagree, you can:
1. Manually override the grade, OR
2. Adjust the rubric and re-grade, OR
3. Contact support (token cost is minimal for re-grading)

---

## Summary

✅ **Student template ready** — Distribute `notebooks/templates/GW08_table3_two_cols_student_template.ipynb`
✅ **Autograder validated** — Tested on 10 realistic test cases
✅ **Rubric explicit** — 12 clear criteria with 9 CRITICAL RULES
✅ **Output formats clear** — JSON (records) + Markdown (feedback)
✅ **Edge cases documented** — 23 risks identified & mitigated

**Ready to grade student submissions!**

---

**Questions?** Check:
- `PROJECT_COMPLETION_SUMMARY.md` — Full project overview
- `AUTOGRADER_ENHANCEMENT_REPORT.md` — Validation results
- `EDGE_CASES_AND_FALSE_POSITIVES.md` — Known issues & mitigations
