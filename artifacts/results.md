| split    | model               | features      |   roc_auc |   pr_auc |   precision@10% |   lift@10% |   base_rate |   mean_predicted |   brier |
|:---------|:--------------------|:--------------|----------:|---------:|----------------:|-----------:|------------:|-----------------:|--------:|
| temporal | prior               | no duration   |    0.5    |   0.3111 |          0.3261 |     1.0483 |      0.3111 |           0.0674 |  0.2737 |
| temporal | logistic_regression | no duration   |    0.6829 |   0.4849 |          0.5261 |     1.6913 |      0.3111 |           0.1664 |  0.2269 |
| temporal | gradient_boosting   | no duration   |    0.6786 |   0.4725 |          0.5272 |     1.6948 |      0.3111 |           0.1482 |  0.2274 |
| temporal | prior               | with duration |    0.5    |   0.3111 |          0.3261 |     1.0483 |      0.3111 |           0.0674 |  0.2737 |
| temporal | logistic_regression | with duration |    0.7653 |   0.5575 |          0.6022 |     1.9359 |      0.3111 |           0.171  |  0.2145 |
| temporal | gradient_boosting   | with duration |    0.7729 |   0.5452 |          0.5717 |     1.8381 |      0.3111 |           0.1515 |  0.2237 |
| random   | prior               | no duration   |    0.5    |   0.117  |          0.1283 |     1.0968 |      0.117  |           0.117  |  0.1033 |
| random   | logistic_regression | no duration   |    0.7716 |   0.4111 |          0.4923 |     4.2074 |      0.117  |           0.1169 |  0.0851 |
| random   | gradient_boosting   | no duration   |    0.8026 |   0.4648 |          0.5221 |     4.4627 |      0.117  |           0.1167 |  0.0804 |
| random   | prior               | with duration |    0.5    |   0.117  |          0.1283 |     1.0968 |      0.117  |           0.117  |  0.1033 |
| random   | logistic_regression | with duration |    0.9056 |   0.5451 |          0.6018 |     5.1435 |      0.117  |           0.1163 |  0.0714 |
| random   | gradient_boosting   | with duration |    0.9343 |   0.6323 |          0.6338 |     5.4177 |      0.117  |           0.1151 |  0.0615 |
