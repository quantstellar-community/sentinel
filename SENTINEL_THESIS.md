# Sentinel Thesis

## 1. Purpose

Sentinel is an experimental platform for behavioral anomaly intelligence in
dynamic systems.

The first application is online payment fraud detection. Fraud detection is
the initial validation domain, not the final scope of the project.

Sentinel does not primarily aim to build the largest fraud-classification
benchmark. Its purpose is to investigate whether a system can learn normal
transaction behavior and identify deviations from that normality, with quantum
representations evaluated as a potential enhancement.

## 2. Core Thesis

> Sentinel should learn the structure of normal behavior first, then detect
> meaningful deviations from it.

The central research question is:

> Can a quantum feature representation improve one-class anomaly detection
> compared with a classical counterpart under the same data, feature, and
> evaluation constraints?

The project must preserve the distinction between:

- anomaly detection;
- fraud-risk scoring;
- final fraud classification or investigation.

An anomaly is not automatically fraud. It is evidence that a transaction or
behavioral state differs from the learned normal pattern.

## 3. Initial Scope

The first implementation must remain deliberately small.

### Classical models

| Model | Role |
|---|---|
| Logistic Regression | Linear supervised baseline |
| LightGBM | Strong classical supervised baseline |
| Classical OCSVM | Direct counterpart for the quantum anomaly model |

### Quantum models

| Model | Role |
|---|---|
| Quantum Kernel OCSVM | First quantum experiment |
| Quantum Autoencoder | Later phase, only after the first quantum experiment is stable |

XGBoost and LightGBM should not both be part of the initial core. Current
internal evidence favors LightGBM, but that conclusion must be rechecked after
the evaluation protocol is corrected and rerun.

## 4. Model Responsibilities

### Logistic Regression

Provides a simple and interpretable linear reference point. It answers how
much signal can be captured without a highly nonlinear model.

### LightGBM

Provides the strongest classical supervised reference for the initial fraud
task. It represents the practical performance ceiling of the supervised
branch, not the main scientific contribution of Sentinel.

### Classical OCSVM

Learns the boundary of normal data without using fraud labels. It is the
required classical counterpart for Quantum Kernel OCSVM.

### Quantum Kernel OCSVM

Uses a quantum feature map or quantum kernel to represent similarity between
transactions or behavioral states. It should be evaluated as an anomaly
detection experiment, not as a direct replacement for LightGBM.

### Quantum Autoencoder

Will be evaluated only after the Quantum Kernel OCSVM experiment has produced a
reliable baseline. Its classical counterpart must be defined before the
experiment begins.

## 5. Dataset Boundaries

The European credit-card dataset is suitable for an initial controlled
benchmark because it is highly imbalanced and widely used for fraud research.

However, it has important limitations:

- no customer identity;
- no merchant identity;
- no device or location history;
- anonymized PCA features;
- only a short observation period.

Therefore, it can evaluate quantum anomaly methods, but it cannot fully validate
long-term customer behavioral trajectories.

The project must not claim complete behavioral intelligence based only on this
dataset.

A richer dataset may be introduced later only when it answers a clearly defined
research question about entities, temporal behavior, or distribution shift.

## 6. Evaluation Contract

Every model must use the same:

- temporal train/validation/test protocol;
- feature subset;
- preprocessing policy;
- training sample budget;
- anomaly contamination assumption;
- evaluation cases;
- random seed policy.

The main metrics are:

- AUPRC;
- precision and recall;
- Precision@k;
- ROC-AUC as a secondary metric;
- false-positive behavior;
- robustness under temporal or distribution shift.

Accuracy must not be used as the main success criterion.

Quantum advantage must never be assumed. A quantum model is considered
valuable only if its improvement is reproducible and remains meaningful after
accounting for:

- feature count;
- sample count;
- preprocessing;
- simulator noise;
- circuit depth;
- runtime;
- classical baseline strength.

## 7. First Milestone

The first milestone is complete when the following pipeline is reproducible:

```text
Dataset
    -> Leakage-safe temporal split
    -> Shared preprocessing
    -> Classical OCSVM
    -> Quantum Kernel OCSVM
    -> Paired evaluation
    -> Honest conclusion
```

The milestone must answer one question:

> Does the quantum kernel provide measurable value over classical OCSVM on the
> same anomaly-detection problem?

The acceptable outcomes are:

1. quantum improvement is demonstrated;
2. quantum improvement is not demonstrated;
3. quantum helps only under specific constraints.

A negative result is still a valid research result. It must not automatically
trigger the addition of more models.

## 8. Lessons Preserved from the Previous Research Branch

The previous branch produced useful evidence, but it expanded beyond the
project thesis.

The following lessons must be preserved:

1. Supervised models can outperform anomaly models when validation fraud is
   similar to training fraud.
2. Anomaly detection must be tested on novel behavior or distribution shift,
   not only standard fraud ranking.
3. Behavioral features are not automatically useful when the dataset already
   contains related aggregate features.
4. Recent data may be more useful than the entire historical dataset in an
   evolving fraud environment.
5. Anomaly models should be trained on a clearly defined normal population.
6. A high number of models does not compensate for an unclear research
   question.
7. Reproducible temporal evaluation is more important than a larger
   leaderboard.
8. Current experiment results are internal evidence, not proof of production
   performance.

## 9. Explicit Non-Goals

The initial Sentinel implementation will not include:

- 20+ model variants;
- both XGBoost and LightGBM in the core;
- complex hyperparameter search;
- production real-time serving;
- a complete AML platform;
- cybersecurity, aerospace, or data-center adapters;
- a full graph intelligence system;
- a claim of quantum advantage without controlled evidence;
- Quantum Autoencoder before Quantum Kernel OCSVM is evaluated.

## 10. Definition of Done

The initial version is complete when:

- the three classical models run reproducibly;
- Quantum Kernel OCSVM runs on the same controlled setup;
- the comparison is leakage-safe;
- AUPRC and operational metrics are reported;
- the quantum and classical models use equivalent constraints;
- at least one temporal or novel-behavior evaluation is performed;
- the conclusion clearly states what was and was not demonstrated.

## 11. Anti-Drift Rule

Before adding any model, feature group, dataset, metric, or subsystem, answer:

> What specific thesis question does this addition test?

If the answer is unclear, the addition does not belong in the current Sentinel
core.

Sentinel should prefer one well-designed experiment over a large collection of
weakly connected experiments.
