# IssueAssociator

## Overview

The `IssueAssociator` class is designed to associate detected issues from a model output with ground truth issues based on text similarity. This association uses a similarity threshold and outputs associated and unassociated issues, along with basic evaluation metrics like true positives, false positives, and false negatives.

## Output Data Format

The `IssueAssociator` class provides several output methods to retrieve association results and metrics. Below are descriptions of each method’s output format:

### 1. `get_associations()`

Returns a list of dictionaries, each containing an association between a detected issue and a ground truth issue, along with a similarity score. Each dictionary includes the following fields:

- `detected_issue`: Dictionary containing details of the detected issue from the model output.
- `ground_truth_issue`: Dictionary containing details of the matched ground truth issue.
- `score`: Float value representing the similarity score (between 0 and 1).
- `type`: String specifying the issue type (e.g., "Spelling and Grammar", "Definitive language").

Example Output:
```python
[
    {
        "detected_issue": { ... },
        "ground_truth_issue": { ... },
        "score": 0.85,
        "type": "Spelling and Grammar"
    },
    ...
]
```

### 2. `get_unassociated_model_output()`

Returns a list of dictionaries for detected issues that could not be associated with any ground truth issue based on the similarity threshold.

Example Output:
```python
[
    { "location": { "source_sentence": "Detected sentence 1" }, "type": "Spelling and Grammar" },
    { "location": { "source_sentence": "Detected sentence 2" }, "type": "Definitive language" },
    ...
]
```

### 3. `get_unassociated_ground_truth()`

Returns a list of dictionaries for ground truth issues that could not be matched with any detected issue.

Example Output:
```python
[
    { "location": { "source_sentence": "Ground truth sentence 1" }, "type": "Spelling and Grammar" },
    { "location": { "source_sentence": "Ground truth sentence 2" }, "type": "Definitive language" },
    ...
]
```

### 4. `get_true_positives()`

Returns the number of true positives, which are the issues successfully associated between detected and ground truth issues.

Example Output:
```python
5
```

### 5. `get_false_positives()`

Returns the number of false positives, which are the issues detected by the model but unassociated with any ground truth issue.

Example Output:
```python
3
```

### 6. `get_false_negatives()`

Returns the number of false negatives, which are ground truth issues that were not matched with any detected issue.

Example Output:
```python
2
```

## Example Usage

Here’s an example of how to use the `IssueAssociator` class and access its output:

```python
# Initialize IssueAssociator with detected and ground truth issues
associator = IssueAssociator(detected_issues, ground_truth_issues, threshold=0.8)

# Perform the association
associator.associate_issues()

# Retrieve associations and unassociated issues
associations = associator.get_associations()
unassociated_model_output = associator.get_unassociated_model_output()
unassociated_ground_truth = associator.get_unassociated_ground_truth()

# Retrieve evaluation metrics
true_positives = associator.get_true_positives()
false_positives = associator.get_false_positives()
false_negatives = associator.get_false_negatives()
```

This class and its methods enable an in-depth analysis of model performance in detecting issues, facilitating model evaluation and refinement.

--- 

# MetricsCalculator

## Overview

The `MetricsCalculator` class processes results from an instance of `IssueAssociator` and calculates key metrics for evaluating model performance on issue detection. These metrics include precision, recall, true positives, false positives, and false negatives, which are computed per issue type.

## Output Data Format

The `MetricsCalculator` class provides several methods to retrieve metrics, grouped by issue type, and to save or log results. Below are descriptions of each method’s output format:

### 1. `calculate_false_positives_per_type()`

Returns a dictionary with the count of false positives for each issue type, based on detected issues that were unassociated with any ground truth.

Example Output:
```python
{
    "grammar and spelling": 3,
    "definitive language": 2,
    ...
}
```

### 2. `calculate_true_positives_per_type()`

Returns a dictionary with the count of true positives for each issue type, based on successfully associated detected and ground truth issues.

Example Output:
```python
{
    "grammar and spelling": 5,
    "definitive language": 7,
    ...
}
```

### 3. `calculate_false_negatives_per_type()`

Returns a dictionary with the count of false negatives for each issue type, based on ground truth issues that could not be matched with detected issues.

Example Output:
```python
{
    "grammar and spelling": 4,
    "definitive language": 1,
    ...
}
```

### 4. `calculate_precision_per_type(tp=None, fp=None)`

Calculates and returns precision for each issue type, defined as `TP / (TP + FP)`. If `tp` and `fp` arguments are provided, it uses them; otherwise, it derives values from the associated and unassociated issues.

Example Output:
```python
{
    "grammar and spelling": 0.62,
    "definitive language": 0.78,
    ...
}
```

### 5. `calculate_recall_per_type(tp=None, fn=None)`

Calculates and returns recall for each issue type, defined as `TP / (TP + FN)`. If `tp` and `fn` arguments are provided, it uses them; otherwise, it derives values from the associated and unassociated issues.

Example Output:
```python
{
    "grammar and spelling": 0.83,
    "definitive language": 0.91,
    ...
}
```

### 6. `calculate_metrics_per_type()`

Calculates both precision and recall for each issue type, returning them as a dictionary.

Example Output:
```python
{
    "grammar and spelling": {
        "precision": 0.62,
        "recall": 0.83
    },
    "definitive language": {
        "precision": 0.78,
        "recall": 0.91
    },
    ...
}
```

### 7. `write_metrics_to_promptflow_per_type(metrics: dict)`

Writes each metric (precision and recall) per issue type to the Promptflow dashboard for visualization or further analysis.

### 8. `save_results_to_json(results)`

Saves a dictionary of metrics to a JSON-formatted string. This can be used to store calculated metrics in a file or for further analysis.

Example Output:
```json
{
    "precision": {
        "grammar and spelling": 0.62,
        "definitive language": 0.78,
        ...
    },
    "recall": {
        "grammar and spelling": 0.83,
        "definitive language": 0.91,
        ...
    }
}
```

### 9. `calculate_metrics_from_multiple_results(results)`

Calculates aggregated precision and recall per type from multiple sets of results. Each result dictionary in `results` should contain `tp`, `fp`, and `fn` values for each issue type.

Example Output:
```python
{
    "precision": {
        "grammar and spelling": 0.65,
        "definitive language": 0.76,
        ...
    },
    "recall": {
        "grammar and spelling": 0.82,
        "definitive language": 0.89,
        ...
    },
    "tp": {
        "grammar and spelling": 10,
        "definitive language": 15,
        ...
    },
    "fn": {
        "grammar and spelling": 3,
        "definitive language": 2,
        ...
    },
    "fp": {
        "grammar and spelling": 5,
        "definitive language": 4,
        ...
    }
}
```

## Example Usage

Here’s an example of how to use the `MetricsCalculator` class in conjunction with `IssueAssociator`:

```python
# Initialize IssueAssociator and associate issues
issue_associator = IssueAssociator(detected_issues, ground_truth_issues)
issue_associator.associate_issues()

# Initialize MetricsCalculator with the IssueAssociator instance
metrics_calculator = MetricsCalculator(issue_associator)

# Calculate various metrics
false_positives = metrics_calculator.calculate_false_positives_per_type()
true_positives = metrics_calculator.calculate_true_positives_per_type()
false_negatives = metrics_calculator.calculate_false_negatives_per_type()

precision_per_type = metrics_calculator.calculate_precision_per_type()
recall_per_type = metrics_calculator.calculate_recall_per_type()
metrics_per_type = metrics_calculator.calculate_metrics_per_type()

# Save results to JSON
results_json = metrics_calculator.save_results_to_json(metrics_per_type)
```

This class provides a detailed view of model performance across different types of issues, facilitating thorough evaluation and analysis.