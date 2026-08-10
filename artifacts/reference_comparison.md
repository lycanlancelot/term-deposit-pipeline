# Reference model comparison

Temporal split, no `duration`. CIs are 95% percentile bootstrap (n=1000); the
delta is a *paired* bootstrap of logistic minus GBM on identical resamples.
A delta interval covering zero means the models cannot be told apart here.

| metric | logistic | 95% CI | GBM | 95% CI | delta (L−G) 95% CI |
| --- | --- | --- | --- | --- | --- |
| roc_auc | 0.6829 | (0.6705, 0.6947) | 0.6786 | (0.6665, 0.6898) | (-0.0048, 0.0144) |
| pr_auc | 0.4849 | (0.4657, 0.5047) | 0.4725 | (0.4539, 0.4917) | (0.0014, 0.0233) |
