document.addEventListener('DOMContentLoaded', () => {
    const handleInput = document.getElementById('handleInput');
    const recommendBtn = document.getElementById('recommendBtn');
    const btnText = recommendBtn.querySelector('.btn-text');
    const spinner = recommendBtn.querySelector('.spinner');
    const errorMsg = document.getElementById('errorMsg');
    const resultsHeader = document.getElementById('resultsHeader');
    const targetHandleSpan = document.getElementById('targetHandle');
    const cardsContainer = document.getElementById('cardsContainer');
    const themeToggle = document.getElementById('themeToggle');

    let currentProblems = [];
    let currentHandle = '';

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
            if (prob.difficulty_category === 'Easy') diffColor = '#10b981';
            else if (prob.difficulty_category === 'Medium') diffColor = '#f59e0b';
            else if (prob.difficulty_category === 'Hard') diffColor = '#ef4444';

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
        btn.addEventListener('click', (e) => {
            if (currentProblems.length === 0) return;
            
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            const filter = e.target.dataset.filter;
            if (filter === 'All') {
                renderCards(currentProblems, currentHandle);
            } else {
                const filtered = currentProblems.filter(p => p.difficulty_category === filter);
                renderCards(filtered, currentHandle);
            }
        });
    });
});
