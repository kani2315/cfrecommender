document.addEventListener('DOMContentLoaded', () => {
    const handleInput = document.getElementById('handleInput');
    const recommendBtn = document.getElementById('recommendBtn');
    const btnText = recommendBtn.querySelector('.btn-text');
    const spinner = recommendBtn.querySelector('.spinner');
    const errorMsg = document.getElementById('errorMsg');
    const resultsHeader = document.getElementById('resultsHeader');
    const targetHandleSpan = document.getElementById('targetHandle');
    const cardsContainer = document.getElementById('cardsContainer');
    const analysisContainer = document.getElementById('analysisContainer');
    const themeToggle = document.getElementById('themeToggle');

    let currentProblems = [];
    let currentHandle = '';
    let currentAnalysis = null;

    // Theme Management
    const currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    themeToggle.textContent = currentTheme === 'light' ? '🌙' : '☀️';

    themeToggle.addEventListener('click', () => {
        let theme = document.documentElement.getAttribute('data-theme');
        if (theme === 'light') {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
            themeToggle.textContent = '☀️';
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
            themeToggle.textContent = '🌙';
        }
    });

    // Function to get the correct color based on Codeforces rating
    function getRatingColor(rating) {
        if (!rating) return 'var(--text-muted)';
        if (rating < 1200) return 'var(--cf-newbie)';
        if (rating < 1400) return 'var(--cf-pupil)';
        if (rating < 1600) return 'var(--cf-specialist)';
        if (rating < 1900) return 'var(--cf-expert)';
        if (rating < 2100) return 'var(--cf-cm)';
        if (rating < 2300) return 'var(--cf-master)';
        if (rating < 2400) return 'var(--cf-master)'; // Intl Master
        if (rating < 2600) return 'var(--cf-gm)';
        if (rating < 3000) return 'var(--cf-gm)'; // Intl GM
        return 'var(--cf-gm)'; // Legendary GM
    }

    // Handle button click or Enter key
    async function fetchRecommendations() {
        const handle = handleInput.value.trim();
        
        if (!handle) {
            showError('Please enter a Codeforces handle.');
            return;
        }

        // UI Loading State
        errorMsg.classList.add('hidden');
        resultsHeader.classList.add('hidden');
        cardsContainer.innerHTML = '';
        btnText.classList.add('hidden');
        spinner.classList.remove('hidden');
        recommendBtn.disabled = true;

        try {
            // Fetch from our FastAPI backend
            const response = await fetch(`/recommend/${handle}`);
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to fetch recommendations.');
            }

            const data = await response.json();
            
            if (data.length === 0) {
                showError(`No recommendations found for ${handle}. Maybe they solved everything?`);
                return;
            }

            currentProblems = data;
            currentHandle = handle;
            
            // Reset filters to All
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            document.querySelector('.filter-btn[data-filter="All"]').classList.add('active');
            
            analysisContainer.classList.add('hidden');
            cardsContainer.classList.remove('hidden');

            renderCards(currentProblems, currentHandle);

        } catch (error) {
            showError(error.message);
        } finally {
            // Restore UI State
            btnText.classList.remove('hidden');
            spinner.classList.add('hidden');
            recommendBtn.disabled = false;
        }
    }

    function renderCards(problems, handle) {
        cardsContainer.innerHTML = '';
        targetHandleSpan.textContent = handle;
        resultsHeader.classList.remove('hidden');
        
        problems.forEach((prob, index) => {
            const card = document.createElement('a');
            card.href = `https://codeforces.com/problemset/problem/${prob.id.match(/\d+/)[0]}/${prob.id.match(/[A-Z][0-9]*/)[0]}`;
            card.target = '_blank';
            card.className = 'card fade-in';
            card.style.animationDelay = `${index * 0.05}s`;
            
            const ratingColor = getRatingColor(prob.rating);
            card.style.setProperty('--rating-color', ratingColor);

            // Tags
            const tagsHtml = prob.tags.split(',')
                .map(t => `<span class="tag">${t.trim()}</span>`)
                .join('');
                
            let diffColor = 'var(--text-muted)';
            if (prob.difficulty_category === "Let's Improve These") diffColor = '#f59e0b';
            else if (prob.difficulty_category === 'Step Out of Your Comfort Zone') diffColor = '#8b5cf6';

            // Format probability as percentage
            const percent = (prob.predicted_solve_probability * 100).toFixed(1) + '%';

            card.innerHTML = `
                <div class="card-header">
                    <div>
                        <span class="problem-id">${prob.id}</span>
                        <h3 class="problem-name">${prob.name}</h3>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 0.25rem;">
                        <span class="rating-tag">${prob.rating || 'Unrated'}</span>
                        <span class="diff-badge" style="background: ${diffColor}20; color: ${diffColor}; border: 1px solid ${diffColor}; font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; font-weight: 600;">${prob.difficulty_category}</span>
                    </div>
                </div>
                <div class="tags">
                    ${tagsHtml}
                </div>
            `;

            cardsContainer.appendChild(card);
        });
    }

    function showError(msg) {
        errorMsg.textContent = msg;
        errorMsg.classList.remove('hidden');
    }

    // Event Listeners
    recommendBtn.addEventListener('click', fetchRecommendations);
    handleInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            fetchRecommendations();
        }
    });

    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            if (currentProblems.length === 0) return;
            
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            const filter = e.target.dataset.filter;
            
            if (filter === 'Analysis') {
                cardsContainer.classList.add('hidden');
                analysisContainer.classList.remove('hidden');
                
                if (!currentAnalysis || currentAnalysis.handle !== currentHandle) {
                    analysisContainer.innerHTML = '<div class="spinner" style="margin: 4rem auto; border-top-color: var(--primary);"></div>';
                    try {
                        const res = await fetch(`/analysis/${currentHandle}`);
                        if (!res.ok) throw new Error('Failed to fetch analysis');
                        currentAnalysis = await res.json();
                        renderAnalysis(currentAnalysis);
                    } catch (err) {
                        analysisContainer.innerHTML = `<p class="error-msg">${err.message}</p>`;
                    }
                } else {
                    renderAnalysis(currentAnalysis);
                }
            } else {
                analysisContainer.classList.add('hidden');
                cardsContainer.classList.remove('hidden');
                
                if (filter === 'All') {
                    renderCards(currentProblems, currentHandle);
                } else {
                    const filtered = currentProblems.filter(p => p.difficulty_category === filter);
                    renderCards(filtered, currentHandle);
                }
            }
        });
    });

    function renderAnalysis(data) {
        let strongHtml = data.strong_topics.map(t => `
            <div class="topic-row">
                <span class="topic-name">${t.tag}</span>
                <div class="topic-stats">
                    ${t.solved}/${t.attempts} <span class="win-rate high">${(t.win_rate * 100).toFixed(0)}%</span>
                </div>
            </div>
        `).join('') || '<p style="color: var(--text-muted)">Not enough data</p>';
        
        let weakHtml = data.weak_topics.map(t => `
            <div class="topic-row">
                <span class="topic-name">${t.tag}</span>
                <div class="topic-stats">
                    ${t.solved}/${t.attempts} <span class="win-rate low">${(t.win_rate * 100).toFixed(0)}%</span>
                </div>
            </div>
        `).join('') || '<p style="color: var(--text-muted)">Not enough data</p>';

        let avoidedHtml = (data.avoided_topics || []).map(t => `
            <div class="topic-row">
                <span class="topic-name" style="color: var(--text-muted)">${t}</span>
                <div class="topic-stats">
                    <span class="win-rate" style="color: var(--text-muted)">0 attempts</span>
                </div>
            </div>
        `).join('') || '<p style="color: var(--text-muted)">None</p>';

        const ratings = Object.keys(data.rating_stats).map(Number).sort((a,b)=>a-b);
        const maxCount = Math.max(...Object.values(data.rating_stats), 1);
        
        let chartHtml = ratings.map(r => {
            const count = data.rating_stats[r];
            const height = (count / maxCount) * 100;
            return `
                <div class="bar-col" title="${count} solved">
                    <div class="bar-fill" style="height: ${height}%"></div>
                    <span class="bar-label">${r}</span>
                </div>
            `;
        }).join('');

        analysisContainer.innerHTML = `
            <div class="analysis-header-card">
                <h3>Current Rating</h3>
                <div class="analysis-rating" style="color: ${getRatingColor(data.current_rating)}">${data.current_rating}</div>
                <div class="analysis-range">🎯 Sweet Spot: <strong>${data.rating_range[0]} - ${data.rating_range[1]}</strong></div>
            </div>
            
            <div class="analysis-grid">
                <div class="analysis-card">
                    <h4>💪 Strongest Topics</h4>
                    ${strongHtml}
                </div>
                
                <div class="analysis-card">
                    <h4>⚠️ Weakest Topics</h4>
                    ${weakHtml}
                </div>
                
                <div class="analysis-card">
                    <h4>🙈 Avoided Topics</h4>
                    ${avoidedHtml}
                </div>
            </div>
            
            <div class="analysis-card">
                <h4>📊 Rating Distribution</h4>
                <div class="bar-chart">
                    ${chartHtml}
                </div>
            </div>
        `;
    }
});
