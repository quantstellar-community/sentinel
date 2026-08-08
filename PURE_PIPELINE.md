# Pipeline Logic & Mathematics — End-to-End

This document describes every transformation, model, and decision the pipeline performs, expressed purely in logic and mathematics. No source files or programming constructs are referenced.

---

## Overview — Execution Phases

The pipeline runs five sequential phases:

| Phase | Purpose |
|-------|---------|
| **1 — Data Extraction** | Load raw transactions and enrich with rolling windows, behavioral statistics, and statistical deviation scores |
| **2 — Feature Engineering** | Derive domain-specific fraud signals: Z-scores, velocity ratios, demographic features, night-ratio |
| **3 — Training** | Learn a semi-supervised classifier through Positive-Unlabeled learning with spy filtering and cross-validated noise removal |
| **4 — Tiered Inference** | Three-tier hierarchical routing: fast rule bypass → ML classification → causal explanation |
| **5 — Continuous Learning** | Demonstrate Elastic Weight Consolidation to prevent catastrophic forgetting under distribution drift |

---

## Phase 1 — Data Extraction

### 1.1 Raw Transaction Retrieval

Each record represents one banking transaction. The following base fields are retrieved per transaction:

- Customer identifier
- Transaction type (two-level hierarchy), date, hour, day-of-week, sequence number
- Transaction amount
- Beneficiary customer identifier, device operating system, IP proxy flag
- Customer demographic profile: sex, account creation date, date of birth, staff flag, internet banking registration date, registration channel, SMS flag, verification method

### 1.2 Rolling Window Aggregates

For each transaction, rolling aggregates are computed over the same customer's prior transaction history using a continuous timestamp (Julian day + fractional hour). Six window sizes are used:

| Window | Metrics |
|--------|---------|
| 1 hour | Sum of amounts, Count of transactions |
| 3 hours | Sum of amounts, Count of transactions |
| 24 hours | Sum of amounts, Count of transactions |
| 48 hours | Sum of amounts, Count of transactions |
| 7 days | Sum of amounts, Count of transactions |
| 30 days | Sum of amounts, Count of transactions |

Each window includes the current row (i.e., "up to and including now").

### 1.3 Customer-Level Historical Aggregates

Two lifetime aggregates are joined per customer:

- **Historical average account balance**: Mean of `AVG_CA_BALANCE` across all deposit snapshots for the customer.
- **Historical average transaction amount**: Mean of `TRANS_AMOUNT` across all of the customer's past transactions, along with their total historical transaction count.

### 1.4 Time Gap: Days Since Last Transaction

For each transaction, the elapsed time in days since the same customer's immediately preceding transaction is computed:

$$\text{DAYS\_SINCE\_LAST\_TRANS}_i = \frac{t_i - t_{i-1}}{86400} \quad \text{(seconds → days)}$$

If no prior transaction exists, fallback to the number of days since the customer's internet banking registration date (or account creation date). If neither exists, default to 999.

### 1.5 Unique Beneficiaries in 24 Hours

A sliding-window count of distinct outbound beneficiary customer identifiers within the trailing 24-hour window for each transaction. Uses a two-pointer sweep per customer:

$$\text{UNIQUE\_BENEFICIARIES\_24H}_i = \bigl|\{b_j : t_j \in [t_i - 24\text{h},\; t_i],\; b_j \ne \text{UNKNOWN}\}\bigr|$$

### 1.6 Security Event Proximity

From the customer activity log, security-sensitive events are isolated:

> PASSWORD_CHANGE, PASSWORD_SET, PIN_SET, PIN_CHANGE, PIN_RESET, ADDRESS_BOOK_UPDATE

For each transaction, the elapsed hours since the customer's most recent security event (occurring at or before the transaction) is computed:

$$\text{HOURS\_SINCE\_SEC\_EVENT}_i = \frac{t_{\text{tx},i} - t_{\text{last\_sec},i}}{3600}$$

Default: 999 if no prior security event exists.

### 1.7 Login Channel & Biometric Statistics

From the customer activity log, login events are isolated (standard login, fingerprint login, face-ID login). For each transaction, the most recent login event (at or before the transaction) is found, and the following are carried forward:

- **Last login method**: The authentication type of the most recent login.
- **Cumulative biometric ratio**: Fraction of all prior logins that used biometric authentication (fingerprint or face-ID):

$$\text{HIST\_BIOMETRIC\_RATIO}_i = \frac{\sum_{j<i} \mathbb{1}[\text{login}_j \in \{\text{FINGER}, \text{FACEID}\}]}{\text{total\_logins\_before\_}i + \epsilon}$$

- **Cumulative login count**: Total number of logins before the current event.

### 1.8 Benford's Law Deviation (Per Customer)

For each customer with ≥ 5 transactions, the KL-Divergence of their transaction amount leading-digit distribution from the theoretical Benford's Law distribution is computed.

**Benford's theoretical probability** for leading digit $d \in \{1, \dots, 9\}$:

$$q_d = \log_{10}\!\left(1 + \frac{1}{d}\right)$$

**Observed probability** from the customer's transaction amounts:

$$p_d = \frac{\text{count of transactions with leading digit } d}{\text{total transactions}}$$

**KL-Divergence**:

$$\text{BENFORD\_DEV} = D_{\text{KL}}(P \| Q) = \sum_{d=1}^{9} p_d \cdot \ln\!\left(\frac{p_d}{q_d}\right)$$

Customers with fewer than 5 transactions receive a deviation of 0.

### 1.9 Second-Order Markov Chain Activity Sequence Rarity (Per Customer)

A second-order Markov chain is built over the global activity log (all customers pooled). This models the probability of an activity type given the two preceding activities.

**Count structures built from all customer activity sequences**:

- Global unigram counts: $C(a)$ — total occurrences of activity $a$
- First-order bigram counts: $C(a_1, a_2)$ — count of activity $a_2$ following $a_1$
- Second-order trigram counts: $C(a_1, a_2, a_3)$ — count of $a_3$ following the pair $(a_1, a_2)$

**Probability with interpolated backoff**:

$$P_{\text{global}}(a) = \frac{C(a)}{N_{\text{total}}}$$

$$P_{\text{1st}}(a_2 | a_1) = \begin{cases} \frac{C(a_1, a_2)}{\sum_{a'} C(a_1, a')} & \text{if denominator} > 0 \\ P_{\text{global}}(a_2) & \text{otherwise} \end{cases}$$

$$P_{\text{2nd}}(a_3 | a_1, a_2) = \begin{cases} \frac{C(a_1, a_2, a_3)}{\sum_{a'} C(a_1, a_2, a')} & \text{if denominator} > 0 \\ P_{\text{1st}}(a_3 | a_2) & \text{otherwise} \end{cases}$$

**Interpolated transition probability**:

$$P_{\text{interp}}(a_3 | a_1, a_2) = 0.7 \cdot P_{\text{2nd}}(a_3 | a_1, a_2) + 0.2 \cdot P_{\text{1st}}(a_3 | a_2) + 0.1 \cdot P_{\text{global}}(a_3)$$

**Per-customer rarity score** (length-normalized average log-likelihood):

$$\text{ACTIVITY\_SEQ\_RARITY}_c = \frac{1}{|\text{seq}_c| - 1}\left[\ln P_{\text{1st}}(a_2|a_1) + \sum_{i=1}^{|\text{seq}_c|-2} \ln P_{\text{interp}}(a_{i+2}|a_i, a_{i+1})\right]$$

More negative values → rarer (more unusual) activity sequences.

---

## Phase 2 — Feature Engineering (Preprocessing)

The preprocessor transforms the enriched raw dataframe into a purely numerical feature matrix. The following groups of features are produced:

### 2.1 Demographic Derived Features

| Feature | Formula |
|---------|---------|
| CUSTOMER_AGE | year(transaction date) − year(date of birth), default 35 |
| TENURE_DAYS | transaction date − account creation date, in days |

### 2.2 Base Numerical Features (Pass-Through)

All 27 raw numerical fields from Phase 1 are carried through (coerced to float, NaN → 0):

> TRANS_HOUR, TRANS_NO, TRANS_AMOUNT, STAFF, SMS, HIST_AVG_CA_BALANCE, HIST_AVG_TRANS_AMOUNT, HIST_TRANS_COUNT, BENFORD_DEV, ACTIVITY_SEQ_RARITY, SUM_AMOUNT_{1H,3H,24H,48H,7D,30D}, COUNT_{1H,3H,24H,48H,7D,30D}, DAYS_SINCE_LAST_TRANS, UNIQUE_BENEFICIARIES_24H, HOURS_SINCE_SEC_EVENT, HIST_BIOMETRIC_RATIO, HIST_LOGIN_COUNT

### 2.3 Derived Ratio & Velocity Features

| Feature | Formula | Signal |
|---------|---------|--------|
| TRANS_AMOUNT_Z_SCORE | $\frac{\text{amount}}{\text{hist\_avg\_amount} + \epsilon}$ | How many times larger than personal average |
| BALANCE_COVERAGE_RATIO | $\frac{\text{amount}}{\text{hist\_avg\_balance} + \epsilon}$ | Transaction size relative to savings |
| VELOCITY_RATIO_AMOUNT_1H_VS_24H | $\frac{\text{sum\_1h}}{\text{sum\_24h} + \epsilon}$ | Short-burst amount concentration |
| VELOCITY_RATIO_AMOUNT_24H_VS_7D | $\frac{\text{sum\_24h}}{\text{sum\_7d} + \epsilon}$ | Daily amount spike detection |
| VELOCITY_RATIO_AMOUNT_7D_VS_30D | $\frac{\text{sum\_7d}}{\text{sum\_30d} + \epsilon}$ | Weekly amount spike detection |
| VELOCITY_RATIO_COUNT_1H_VS_24H | $\frac{\text{count\_1h}}{\text{count\_24h} + \epsilon}$ | Short-burst frequency concentration |
| VELOCITY_RATIO_COUNT_24H_VS_7D | $\frac{\text{count\_24h}}{\text{count\_7d} + \epsilon}$ | Daily frequency spike detection |
| VELOCITY_RATIO_COUNT_7D_VS_30D | $\frac{\text{count\_7d}}{\text{count\_30d} + \epsilon}$ | Weekly frequency spike detection |
| TRANS_AMOUNT_VS_30D_AVG_RATIO | $\frac{\text{amount}}{\text{sum\_30d} / (\text{count\_30d} + \epsilon) + \epsilon}$ | Amount vs rolling 30-day average |

Where $\epsilon = 10^{-5}$ prevents division by zero.

### 2.4 Night Transaction Ratio

$$\text{HIST\_NIGHT\_RATIO}_i = \frac{\sum_{j < i} \mathbb{1}[\text{hour}_j \in [0, 5]]}{\text{cumulative\_count\_before\_}i + \epsilon}$$

Fraction of the customer's preceding transactions that occurred during midnight–5AM.

### 2.5 Categorical Encoding

Seven categorical fields are integer-encoded using a fitted label dictionary:

> TRANS_LV1, TRANS_LV2, DAY_OF_WEEK, CLIENT_SEX, EB_REGISTER_CHANNEL, VERIFY_METHOD, Occupation_Group

Unknown/missing values map to a dedicated UNKNOWN category.

**Total feature dimensionality**: ~46 numerical features.

---

## Phase 3 — Training (nnPU with Spy Filtering & CVuO)

This is a Positive-Unlabeled (PU) learning pipeline. No ground-truth fraud labels exist. The pipeline manufactures proxy labels and then trains a gradient-boosted tree classifier with three layers of noise control.

### 3.1 Step 1 — Bootstrap Proxy Labels via Isolation Forest

An Isolation Forest (contamination rate $c = 0.03$) is fitted on all training features. Samples scored as outliers receive proxy label $s = 1$ (suspected positive/anomaly). All others receive $s = 0$ (unlabeled).

$$s_i = \begin{cases} 1 & \text{if IsolationForest classifies } x_i \text{ as anomaly} \\ 0 & \text{otherwise} \end{cases}$$

Let $P = \{i : s_i = 1\}$ and $U = \{i : s_i = 0\}$.

### 3.2 Step 2 — PAYN Spy Filtering

**Goal**: Identify a reliable subset of negatives from the unlabeled pool $U$ by planting known positives ("spies") into it.

1. Randomly select 10% of $P$ as spies: $\text{Spies} \subset P$, $|\text{Spies}| = \lfloor 0.10 \cdot |P| \rfloor$.
2. Train a preliminary XGBoost classifier:
   - Positive class: $P \setminus \text{Spies}$
   - Negative class: $U \cup \text{Spies}$
3. Predict probabilities for the spy samples. Find the 5th percentile of spy prediction scores:

$$\tau_{\text{spy}} = \text{Percentile}_{5}\bigl(\{g(x_j)\}_{j \in \text{Spies}}\bigr)$$

4. Any unlabeled sample with prediction score below $\tau_{\text{spy}}$ is promoted to **confirmed negative**:

$$N_{\text{confirmed}} = \{j \in U : g(x_j) < \tau_{\text{spy}}\}$$

The remainder stays in the ambiguous unlabeled pool: $U_{\text{remaining}} = U \setminus N_{\text{confirmed}}$.

### 3.3 Step 3 — Cross-Validated Unlabeled Optimization (CVuO)

**Goal**: Filter out high-loss (likely mislabeled or adversarial) samples from $U_{\text{remaining}}$.

1. Perform 5-fold cross-validation over $U_{\text{remaining}}$.
2. In each fold, train a temporary XGBoost model on $P \cup N_{\text{confirmed}}$ only.
3. For each held-out unlabeled sample, compute log-loss assuming it is a negative ($y = 0$):

$$\ell_j = -\ln(1 - g(x_j) + 10^{-15})$$

4. Discard the top 10% of $U_{\text{remaining}}$ by loss (these are likely hidden positives contaminating the unlabeled pool):

$$U_{\text{filtered}} = \{j \in U_{\text{remaining}} : \ell_j \leq \text{Percentile}_{90}(\{\ell_k\})\}$$

### 3.4 Step 4 — Final XGBoost Training

Train the production XGBoost classifier on the cleaned label set:

- Positive class: all of $P$
- Negative class: $N_{\text{confirmed}} \cup U_{\text{filtered}}$

**XGBoost hyperparameters** (Rademacher Complexity Regularization):

| Parameter | Value | Purpose |
|-----------|-------|---------|
| n_estimators | 100 | Number of boosting rounds |
| max_depth | 3 | Strict tree depth (complexity bound) |
| reg_alpha ($\alpha$) | 1.0 | L1 weight regularization |
| reg_lambda ($\lambda$) | 2.0 | L2 weight regularization |
| learning_rate ($\eta$) | 0.05 | Shrinkage |

### 3.5 Step 5 — Elkan-Noto Probability Calibration

Raw XGBoost probabilities $g(x)$ are biased because training labels are noisy PU labels, not true labels. The Elkan-Noto correction adjusts for this:

$$\hat{c} = \frac{1}{|P|}\sum_{j \in P} g(x_j)$$

$$P(\text{fraud} | x) = \min\!\left(\frac{g(x)}{\hat{c}},\; 1.0\right)$$

### 3.6 Decision Threshold

The decision threshold is set so that the top $c = 3\%$ of calibrated probabilities across the training set are flagged:

$$\tau = \text{Percentile}_{97}\!\bigl(\{P(\text{fraud}|x_i)\}_{i \in \text{training}}\bigr)$$

A transaction is flagged if $P(\text{fraud}|x) \geq \tau$.

---

## Phase 4 — Tiered Inference & Explanation

### 4.1 Tier 1 — High-Speed Bypass (Rule-Based)

Every transaction is evaluated against fast deterministic rules. A transaction is marked **safe** (prediction = 0, score = 0.0) if EITHER condition holds:

**Condition A (Sequence + Amount)**:
$$\text{ACTIVITY\_SEQ\_RARITY} > -1.0 \;\;\text{AND}\;\; \text{TRANS\_AMOUNT} < 500{,}000$$

**Condition B (Velocity + Amount)**:
$$\text{TRANS\_AMOUNT} < 500{,}000 \;\;\text{AND}\;\; \text{COUNT\_1H} \leq 1 \;\;\text{AND}\;\; \text{COUNT\_24H} \leq 2$$

Safe transactions skip all downstream ML processing. Empirically ~95% of traffic is filtered here.

### 4.2 Tier 2 — ML Classification (Ambiguous Events)

Transactions that fail Tier 1 are preprocessed through Phase 2 feature engineering, then scored by the trained XGBoost classifier with Elkan-Noto calibration.

Each ambiguous transaction receives:
- Binary prediction: $\hat{y} = \mathbb{1}[P(\text{fraud}|x) \geq \tau]$
- Calibrated anomaly score: $P(\text{fraud}|x)$

### 4.3 Tier 3 — Causal Explanation (Flagged Anomalies Only)

For each flagged anomaly ($\hat{y} = 1$), three explanation artifacts are generated:

#### 4.3.1 SHAP Feature Contributions

A TreeSHAP explainer computes per-feature additive contribution values $\phi_j$ for the flagged instance.

$$g(x) = \phi_0 + \sum_{j=1}^{F} \phi_j$$

Where $\phi_0$ is the base value and $\phi_j$ is the marginal contribution of feature $j$. Features are ranked by contribution magnitude. The top 3 positive contributors are selected and translated into a natural-language narrative using a deterministic template system.

**Narrative template examples**:

| Feature | Narrative Pattern |
|---------|-------------------|
| ACTIVITY_SEQ_RARITY | "highly improbable sequential activity pattern (log-probability score: X)" |
| VELOCITY_RATIO_COUNT_24H_VS_7D | "sudden transaction frequency spike (24h count is X% of 7d count)" |
| TRANS_AMOUNT_Z_SCORE | "amount is Xx higher than customer's average transaction size" |
| BENFORD_DEV | "significant transaction amount digit deviation from Benford's Law" |
| BALANCE_COVERAGE_RATIO | "transaction amount covers Xx their monthly average savings balance" |

#### 4.3.2 SHAP Interaction Values

For tree-based models, the full $F \times F$ SHAP interaction matrix $\Phi_{ij}$ is computed. Off-diagonal elements represent the joint interaction effect of feature pairs beyond their individual contributions:

$$\text{Interaction}(i, j) = \Phi_{ij} + \Phi_{ji}$$

The top 3 pairs by absolute interaction value (filtered by $|v| > 0.01$) are reported.

#### 4.3.3 Counterfactual Recourse (Sequential-Causal Binary Search)

For each top contributing feature, the minimum perturbation that would drop the anomaly score below the decision threshold $\tau$ is found via binary search.

**Key constraints**:

1. **Immutable features are blocked**: Customer age, tenure, historical averages, sex, channel, verification method, transaction type, day-of-week, hour, staff flag, SMS flag, sequence number — these cannot be recommended for change.

2. **Causal propagation**: When perturbing a root feature, all mathematically dependent features are recomputed. For TRANS_AMOUNT perturbation from original value $a_0$ to candidate $a'$:

$$\Delta a = a' - a_0$$

$$\text{SUM\_AMOUNT\_}w' = \max(0,\; \text{SUM\_AMOUNT\_}w - a_0 + a')  \quad \forall w \in \{1\text{H}, 3\text{H}, 24\text{H}, 48\text{H}, 7\text{D}, 30\text{D}\}$$

$$\text{Z\_SCORE}' = \frac{a'}{\text{HIST\_AVG\_TRANS\_AMOUNT} + \epsilon}$$

$$\text{BALANCE\_COVERAGE}' = \frac{a'}{\text{HIST\_AVG\_CA\_BALANCE} + \epsilon}$$

$$\text{VELOCITY\_RATIO\_AMOUNT\_}w_1\text{\_VS\_}w_2' = \frac{\text{SUM\_}w_1'}{\text{SUM\_}w_2' + \epsilon}$$

$$\text{TRANS\_AMOUNT\_VS\_30D\_AVG\_RATIO}' = \frac{a'}{\text{SUM\_30D}' / (\text{COUNT\_30D} + \epsilon) + \epsilon}$$

Similarly, for COUNT_24H or COUNT_1H perturbation, dependent count velocity ratios are recalculated.

**Binary search procedure** (20 iterations):

- Search interval: $[\text{column\_min},\; \text{original\_value}]$
- At each step, evaluate midpoint with full causal propagation
- If score drops below $\tau$ → record as safe, try higher (closer to original) to find minimum change
- If score stays above $\tau$ → try lower
- Report only if $|\Delta| > 0.01$

**Output per counterfactual**: feature name, original value, safe value, and delta.

---

## Phase 5 — Continuous Learning with Elastic Weight Consolidation (EWC)

This phase demonstrates resistance to catastrophic forgetting when the model is retrained on drifted data.

### 5.1 Autoencoder Architecture

A symmetric fully-connected autoencoder maps input features through a bottleneck:

$$\text{Encoder}: \mathbb{R}^{D} \xrightarrow{\text{Linear}(D, 16)} \text{ReLU} \xrightarrow{\text{Linear}(16, 8)} \text{ReLU} \rightarrow \mathbb{R}^{8}$$

$$\text{Decoder}: \mathbb{R}^{8} \xrightarrow{\text{Linear}(8, 16)} \text{ReLU} \xrightarrow{\text{Linear}(16, D)} \mathbb{R}^{D}$$

**Input normalization**: All features are z-standardized using training set mean and standard deviation:

$$\tilde{x} = \frac{x - \mu}{\sigma + 10^{-5}}$$

### 5.2 Base Training

The autoencoder is trained to minimize reconstruction error (MSE) over the clean/historical data:

$$\mathcal{L}_{\text{recon}} = \frac{1}{N}\sum_{i=1}^{N} \|x_i - \hat{x}_i\|^2$$

Training uses Adam optimizer with learning rate 0.01 for 5 epochs with mini-batches of 256.

The anomaly threshold is set at the $(1 - c)$-th percentile of per-sample MSE values on the training set (where $c = 0.03$):

$$\tau_{\text{AE}} = \text{Percentile}_{97}(\{\text{MSE}_i\}_{i \in \text{train}})$$

### 5.3 Fisher Information Matrix (FIM) Computation

After base training, the diagonal of the Fisher Information Matrix is computed sample-by-sample. For each parameter $\theta_k$:

$$F_k = \frac{1}{N}\sum_{i=1}^{N}\left(\frac{\partial \mathcal{L}(x_i)}{\partial \theta_k}\right)^2$$

This quantifies how important each weight is for reconstructing the baseline data distribution. The current parameter values are cached as $\theta^*$.

### 5.4 Online Retraining with EWC Penalty

When new (potentially drifted) data arrives, the model is retrained with a quadratic penalty that prevents important weights from shifting too far from their baseline values:

$$\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{recon}}^{\text{new}} + \frac{\lambda_{\text{EWC}}}{2}\sum_k F_k \cdot (\theta_k - \theta_k^*)^2$$

Where $\lambda_{\text{EWC}} = 50.0$ controls the strength of the consolidation penalty.

**Drift simulation**: Transaction amounts are multiplied by 5.0 to simulate behavioral drift. The EWC-protected model retains lower anomaly scores on baseline data compared to a model retrained without the penalty ($\lambda_{\text{EWC}} = 0$), demonstrating resistance to catastrophic forgetting.

### 5.5 Anomaly Scoring (Autoencoder)

At inference time, the anomaly score for a sample is the ratio of its reconstruction MSE to the training threshold:

$$\text{score}(x) = \min\!\left(\frac{\text{MSE}(x)}{\tau_{\text{AE}}},\; 1.0\right)$$

A sample is flagged as anomalous if $\text{score}(x) \geq 1.0$ (i.e., reconstruction error meets or exceeds the threshold).

---

## Output Artifacts

The pipeline produces the following outputs per execution:

| Artifact | Content |
|----------|---------|
| Anomaly alerts CSV | All flagged transactions with: customer ID, binary prediction, calibrated score, narrative, top SHAP contributors, top interaction pairs, counterfactual recourse |
| Metadata JSON | Component class names, timestamp, anomaly count, total records evaluated |
| Evaluation report | Summary statistics, risk distribution, top SHAP features, top interactions, counterfactual coverage |
| Timestamped archive | Immutable copy of alerts CSV and metadata JSON with execution timestamp |
