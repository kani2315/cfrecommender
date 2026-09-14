# FAANG Interview Mastery: Codeforces MLOps Recommender

## Phase 1 – Project Overview

### 1. What problem does this project solve?
*   **The Core Problem:** On competitive programming platforms like Codeforces, users often stagnate. They either solve problems that are too easy (wasting time) or attempt problems that are too hard (destroying confidence). Furthermore, identifying *which* specific topics a user is weak at requires manual, tedious analysis.
*   **The Solution:** This project acts as an automated, highly personalized problem recommender. It mathematically identifies a user's weak or avoided topics and uses a trained Machine Learning model to serve problems that are perfectly targeted to their current skill level, keeping them in the optimal "challenge zone."

### 2. Why was this project built?
*   It was built to bridge the gap between static algorithmic platforms and personalized learning. Traditional platforms just offer a massive list of 10,000+ problems. This project introduces **Machine Learning Operations (MLOps)** to create a dynamic feedback loop: the system learns global difficulty patterns and adapts instantly to the user's live performance.

### 3. What are the main features?
*   **Real-Time Adaptive Difficulty:** Uses live Codeforces API data on every click. If a user solves 10 DP problems, the model instantly adapts and suggests harder DP problems.
*   **Dynamic Target Proximity Algorithm:** Instead of rigid percentage filters, it sorts candidates by how mathematically close they are to a target probability (e.g., Easy = 75%, Medium = 50%, Hard = 25%).
*   **Profile Analysis Dashboard:** Calculates continuous metrics like "Weighted Strength Score" (`solved * win_rate`) and "Proportional Avoidance Ratio" (`Global Frequency / (User Attempts + 1)`).
*   **End-to-End MLOps Pipeline:** A 24-hour embedded background scheduler that automatically downloads global data, engineers features, retrains the XGBoost model, and updates the production environment without downtime.

### 4. What technologies are used?
*   **Backend:** FastAPI (Python), Uvicorn
*   **Machine Learning:** XGBoost (`XGBClassifier`), scikit-learn, Pandas, NumPy, joblib
*   **Database:** PostgreSQL, SQLAlchemy (ORM)
*   **Frontend:** Vanilla HTML/CSS/JS (Glassmorphism design)
*   **Deployment & DevOps:** Docker, Docker Compose, Railway (PaaS)

### 5. Why was each technology chosen instead of alternatives?
*   **FastAPI over Django/Flask:** FastAPI's native `asyncio` support was critical. It allowed the ML training scheduler to be embedded as a background task within the same event loop, eliminating the need for a separate worker server (which halves cloud hosting costs).
*   **XGBoost over Deep Learning / Logistic Regression:** Deep Learning is overkill for tabular data (ratings, counts, tags) and requires heavy compute. Logistic Regression failed to capture non-linear relationships (e.g., good at high-rating Math, bad at low-rating Graphs). XGBoost is the industry standard for tabular data, training rapidly while capturing complex interactions.
*   **PostgreSQL over MongoDB:** The system requires complex joining of highly structured relational data (Users, Problems, and their associative Submissions). Relational databases are optimized for these `JOIN` operations.
*   **Vanilla HTML/JS over React:** A Vanilla stack eliminated the complexity of a Node.js build step, allowing the SPA to be served directly through FastAPI's `StaticFiles`.
*   **Railway & Docker over AWS EC2:** Docker ensures the code runs identically locally and in production. Railway natively connects to GitHub and provisions SSL/Databases out-of-the-box, removing manual server maintenance required by EC2.

### 6. Explain the complete architecture.
The architecture is a fully containerized, single-node MLOps environment:
1.  **Data Tier:** A PostgreSQL database stores Users, Problems, and Submissions.
2.  **ML Pipeline (Background):** Inside the FastAPI container, an `asyncio` background task runs every 24 hours. It triggers `fetch_cf_data.py` (fetching 30k+ submissions via stratified sampling) followed by `train.py` (engineering features and retraining XGBoost). The output is saved to a persistent Docker Volume (`/app/models/logistic_model.joblib`).
3.  **Inference Engine (Foreground):** The FastAPI web server (`recommender.py`) holds the `.joblib` model in memory. It exposes REST API endpoints.
4.  **Presentation Tier:** A Vanilla JS frontend that makes asynchronous `fetch()` requests to the FastAPI backend, rendering the UI dynamically.

### 7. Explain the data flow from start to finish.
**Training Flow (Every 24 Hours):**
1.  **Ingestion:** Python script hits Codeforces API -> downloads Problems & Users -> saves to PostgreSQL.
2.  **Processing:** `train.py` queries DB -> joins tables -> engineers features (`user_rating`, `problem_solve_count`, `MultiLabelBinarizer` for tags) -> creates X and y matrices.
3.  **Training:** XGBoost model fits data -> serialized via `joblib` -> saved to persistent volume.

**Inference Flow (User clicks "Find Problems"):**
1.  **Request:** User enters handle in UI -> UI sends `GET /recommend/{handle}`.
2.  **Live Fetch:** FastAPI hits CF API to get user's *current* rating and complete submission history.
3.  **Analysis:** Backend calculates win-rates per topic, identifying "Weak" and "Avoided" tags.
4.  **Candidate Generation:** Queries PostgreSQL for unsolved problems strictly containing those weak/avoided tags, applying a `user_rating ± 300` constraint.
5.  **Prediction:** Candidates are fed into the in-memory XGBoost model, which outputs a probability (`predict_proba`) for each problem.
6.  **Ranking:** Dynamic Target Proximity sorts problems closest to 0.75, 0.50, and 0.25 probabilities.
7.  **Response:** Top 30 problems returned as JSON -> UI renders problem cards.

### 8. Explain how users interact with the application.
1.  The user visits the URL served by FastAPI.
2.  They see a modern glassmorphism UI. They enter their Codeforces handle in a search bar.
3.  The UI makes an API call and instantly transitions (without page reload) to the Profile Analysis Dashboard, displaying a rating distribution bar chart, top 5 strong topics, and top 5 weak topics.
4.  The user selects a difficulty filter tab (Easy, Medium, Hard).
5.  Based on the selected filter, the JavaScript dynamically renders the exact 10 problems targeted at their weakest topics at that specific difficulty level.
