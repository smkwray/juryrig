# Reader FAQ

Short answers to common questions about this project.

---

### What does this project study?

It analyzes public New York State court records to describe patterns in criminal case outcomes. It has two parts: one that estimates conviction likelihood from arraignment data, and one that looks at how pretrial release rates changed around bail-law amendments in 2022 and 2023.

### What is OCA-STAT?

OCA-STAT is a public dataset maintained by the New York State Office of Court Administration. It contains case-level records from criminal arraignments across the state. This project uses OCA-STAT as the main data source for its predictive branch.

### What does the model actually predict?

It estimates the probability that a criminal case will end in conviction (as opposed to dismissal or acquittal). It uses only information available around the time of arraignment — things like county, charge severity, arrest type, gender, ethnicity, and race. It does not use any post-arraignment information.

### How accurate is the model?

The best model correctly classified about 79% of test cases and achieved an AUROC of 0.86 (on a scale from 0.5 to 1.0, where higher is better). In practical terms, it is substantially better than guessing and picks up real patterns, but it is not perfect.

### What does it show about race?

Race is included as a feature in the model. Conviction rates and model accuracy both vary across racial groups. For example, the model ranks cases more accurately for White defendants (AUROC 0.77) than for Black (0.74) or Asian (0.68) defendants. Explaining why these differences exist would require additional data and a different research design.

### What does it show about bail-law amendments?

The pretrial branch compares release rates before and after the May 2022 and June 2023 bail-law amendments. The largest shift was in firearm-related charges after May 2022, where release rates dropped substantially more than for other case types. The June 2023 amendment shows smaller differences.

### What are the biggest patterns in the data?

The two strongest patterns in the predictive branch are:

- **Geography:** NYC courts have a raw conviction rate of about 25%; courts outside NYC have a rate of about 69%.
- **Charge severity:** Felonies have a conviction rate of about 66%; violations have a rate of about 25%.

These dwarf other factors in the data.

### Where does the data come from?

Both datasets are public. The predictive branch uses OCA-STAT arraignment records. The pretrial branch uses the DCJS/OCA supplemental pretrial release file. Both are published by New York State agencies.

### What are the main limitations?

- The predictive model only uses information from the time of arraignment. It does not include plea negotiations, evidence, or other post-arraignment factors.
- The pretrial analysis is a before-and-after comparison, not a controlled experiment.
- Both branches cover New York State only.
- Model accuracy varies by county and demographic group.
