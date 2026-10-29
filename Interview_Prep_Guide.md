# Codeforces MLOps Recommender System - Interview Preparation Guide

## 1. Project Brief Description
An end-to-end Machine Learning Operations (MLOps) pipeline that acts as a highly personalized problem recommender for Codeforces users. It continuously fetches real-time data from the Codeforces API, trains an XGBoost machine learning model on global problem-solving patterns, and serves sub-second, personalized problem recommendations via a FastAPI backend and a modern glassmorphism UI. It intelligently identifies a user's weak topics and suggests problems based on a "Dynamic Target Proximity" algorithm to ensure practice is perfectly tailored to their current skill level.

## 2. Complete Architecture Detail
The system follows a fully automated MLOps lifecycle containerized using Docker and deployed on Railway (PaaS).
- **Data Ingestion (`scripts/fetch_cf_data.py`)**: Runs periodically to connect to the Codeforces API, downloading the global problemset and using **Stratified Sampling** to fetch submissions from 50 diverse users (Beginner to Grandmaster). Stores this in a PostgreSQL database.
- **Model Training (`scripts/train.py`)**: Queries PostgreSQL to join Users, Problems, and Submissions. It engineers numerical and categorical features (e.g., `user_rating`, `problem_rating`, `problem_solve_count`, `tags`), uses `MultiLabelBinarizer` for tags, and trains an **XGBClassifier**. The pipeline is saved as a `.joblib` file.
- **Continuous Integration (Embedded Scheduler)**: To save hosting costs and share volumes on Railway, the background data fetching and model training loop runs inside FastAPI's native `asyncio` event loop. It executes every 24 hours without blocking the web API.
- **Backend / Real-Time Inference (`app/recommender.py`)**: A FastAPI server that loads the `.joblib` model into memory. When a user requests recommendations, it fetches their live stats, calculates their "Avoidance Ratio" and "Weak Topics", queries the DB for unsolved candidates, and uses the model's `predict_proba()` to compute solve probabilities.
- **Frontend**: A Vanilla HTML/CSS/JS Single Page Application (SPA). It uses modern glassmorphism design, requiring no heavy build step (like Node.js), and is served via FastAPI's `StaticFiles`.

## 3. Important Concepts and Algorithms (The "Secret Sauce")
- **XGBoost vs. Logistic Regression**: Swapped Logistic Regression for XGBoost because it handles non-linear relationships better (e.g., a user might be great at high-rating Math problems, but terrible at low-rating Graph problems).
- **Dynamic Target Proximity Algorithm**: Instead of applying strict probability bounds (which can fail for very low or high-rated users), it mathematically sorts problems by how close their solve probability is to a specific target (Easy = 0.75, Medium = 0.50, Hard = 0.25). This scales perfectly to any user's rating curve.
- **Stratified Sampling for Training Data**: Ensures the ML model isn't biased towards Grandmasters by specifically sampling users evenly across 5 skill buckets (Beginner, Pupil, Specialist, Expert, Advanced).
- **Proportional Avoidance Ratio**: Identifies "Avoided Topics" dynamically via `Global Frequency / (User Attempts + 1)` rather than just looking for 0 attempts, preventing obscure topics from polluting suggestions.
- **Weighted Strength Score Heuristic**: Balances volume and efficiency for "Strongest Topics" using `solved * win_rate` to outrank low-volume, high-win-rate flukes.
- **Real-Time Adaptive Difficulty**: The ML background task runs every 24 hours to learn *general patterns*, but the actual recommendation engine pulls the user's *personal stats* live on every click. This means if a user solves 10 DP problems, the engine instantly adapts and suggests harder DP problems.

## 4. Basic Interview Questions (Tech Stack & Choices)

**Q: Why did you choose FastAPI over Flask or Django?**
*A:* FastAPI was chosen for its high performance and native asynchronous capabilities (`asyncio`). It allows us to embed the ML training scheduler as a background task within the same event loop, eliminating the need for a separate worker server (which halves hosting costs). It also integrates seamlessly with Pydantic for data validation.

**Q: Why did you use XGBoost instead of Deep Learning (Neural Networks)?**
*A:* Our dataset is tabular (features like rating, solve count, tags). Neural networks are overkill for tabular data and require massive amounts of data/compute to beat tree-based models. XGBoost is widely considered the state-of-the-art for tabular data, trains extremely fast, and captures complex non-linear relationships efficiently.

**Q: How does the system handle an "Unrated" user who has never participated in a contest?**
*A:* The system scans all the problems the user has solved in practice, fetches the official Codeforces difficulty rating of those problems, and computes the mathematical average to dynamically estimate their "True Hidden Rating" on the fly.

**Q: Why PostgreSQL instead of a NoSQL database like MongoDB?**
*A:* The project requires complex joining of highly structured relational data (Users, Problems, and their associative Submissions). Relational databases like PostgreSQL are optimized for these ACID transactions and `JOIN` operations. We also utilize SQLAlchemy as our ORM to abstract the raw queries.

**Q: Why Vanilla HTML/CSS/JS instead of React or Vue?**
*A:* To eliminate the complexity of a Node.js build step. A Vanilla stack allows us to serve the SPA directly through FastAPI while maintaining a premium glassmorphism UI. It also allows for instant hot-reloading in development via a mounted Docker volume.

**Q: How did you deploy the application and manage background tasks?**
*A:* It's deployed via Docker on Railway (a PaaS). Instead of setting up Kubernetes CronJobs or separate Celery/Redis workers (which increases cost and complexity), the 24-hour ML retraining loop is embedded directly into FastAPI via `asyncio.create_task()`. We attached a persistent Railway Volume to store the `.joblib` model across restarts.
