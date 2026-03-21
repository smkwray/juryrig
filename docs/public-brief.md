# Public Brief

## What this project is

This project analyzes public New York State court records to examine patterns in criminal case outcomes. It has two independent branches, each asking a different question with a different dataset.

## Branch 1: Predicting conviction likelihood

**Question:** Using only information available around the time of arraignment, how well can a statistical model estimate whether a criminal case will end in conviction?

**Data:** About 1.6 million public arraignment records from the OCA-STAT dataset, covering cases filed between 2021 and 2025. The model was tested on a held-out set of 271,701 cases it had not seen during training.

**What the model does:** It takes in case-level details available at arraignment — such as county, charge severity, and arrest type. Protected attributes (gender, ethnicity, race) are excluded from training by default but retained for subgroup auditing — and outputs a probability of conviction. It does not use any information from after arraignment.

**How well it works:** The best-performing model (logistic regression) correctly classified about 78% of cases. Its AUROC score — a measure of how well it ranks cases from least to most likely to end in conviction — was 0.86 out of 1.0. That is substantially better than a coin-flip baseline (0.50) and indicates the model picks up real patterns in the data.

**Strongest patterns:**

- Geography matters most. Cases in NYC courts have a raw conviction rate of about 23%; courts outside NYC have a rate of about 69%.
- Charge severity also matters. Felony cases have a conviction rate of about 66%; violations have a rate of about 25%.
- Model accuracy varies by county. Some counties are much easier for the model to predict than others.

**Race and demographic results:** The model's accuracy differs across racial groups. For example, the model ranks cases more accurately for White defendants (AUROC 0.86) than for Black (0.83) or Asian (0.77) defendants. Raw conviction rates also differ by race.

## Branch 2: Pretrial release rates around bail-law amendments

**Question:** Did pretrial release rates change differently for the types of cases targeted by New York's May 2022 and June 2023 bail-law amendments, compared to other cases?

**Data:** About 854,000 cases from the public DCJS/OCA supplemental pretrial release file, covering January 2021 through December 2024.

**What the analysis does:** It compares release rates in the 12 months before and after each amendment date. It then checks whether the change was larger for the charge categories the amendments targeted than for a broad baseline of all other cases.

**Main findings — May 2022 amendment:**

- The clearest shift appears for firearm-related charges that became newly eligible for detention. In NYC, the release rate for this group dropped about 20 percentage points more than the baseline. Outside NYC, the drop was about 32 percentage points. This group is small (186 cases statewide).
- For a larger group of repeat harm or theft cases (about 164,000 cases), the release rate dropped about 3.7 percentage points more than the baseline in both NYC and non-NYC courts.

**Main findings — June 2023 amendment:**

- The repeat offender group (about 164,000 cases) shows smaller shifts. In NYC, the change was less than 1 percentage point different from the baseline. Outside NYC, the drop was about 2.5 percentage points more than the baseline.

## What these results mean in plain language

Arraignment records contain enough information to sort cases into lower- and higher-likelihood groups with reasonable accuracy. The strongest drivers are geography and charge severity, not demographics.

The pretrial branch shows that release rates shifted around the amendment dates, with the largest shifts in the charge categories the amendments targeted — especially firearm-related charges after May 2022.

## What this project can answer

- What patterns exist in New York arraignment records.
- How well a model can rank cases by conviction likelihood using only arraignment-time data.
- Where model accuracy varies — by county, region, race, gender, and other subgroups.
- Whether pretrial release rates changed more for amendment-targeted charges than for other cases.

## What this project cannot answer

- Why conviction rates differ across groups.
- Whether the bail-law amendments caused the observed release-rate changes.
- How any individual case should be decided.
