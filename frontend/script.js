/**
 * Multi-Agent Research System - Frontend Script
 * Handles API communication and UI interactions
 */

const API_BASE_URL = '';
const STEPS = ['step1', 'step2', 'step3', 'step4'];

// DOM Elements
const searchForm = document.getElementById('searchForm');
const queryInput = document.getElementById('queryInput');
const searchBtn = document.getElementById('searchBtn');
const spinner = document.getElementById('spinner');
const resultsSection = document.getElementById('resultsSection');
const loadingSection = document.getElementById('loadingSection');
const errorSection = document.getElementById('errorSection');

/**
 * Initialize event listeners
 */
function initializeEventListeners() {
    searchForm.addEventListener('submit', handleSearch);
    queryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            handleSearch(e);
        }
    });
}

/**
 * Handle search form submission
 */
async function handleSearch(e) {
    e.preventDefault();

    const query = queryInput.value.trim();
    if (!query) {
        showError('Please enter a research query.');
        return;
    }

    const searchTopN = parseInt(document.getElementById('searchTopN').value);
    const rerankerTopK = parseInt(document.getElementById('rerankerTopK').value);
    const retrieverTopK = parseInt(document.getElementById('retrieverTopK').value);
    const refinementIterations = parseInt(document.getElementById('refinementIterations').value);

    // Validate inputs
    if (searchTopN < 1 || rerankerTopK < 1 || retrieverTopK < 1 || refinementIterations < 0) {
        showError('Invalid parameter values. Please check your settings.');
        return;
    }

    try {
        showLoading();
        disableSearchButton(true);

        const requestPayload = {
            query,
            search_top_n: searchTopN,
            reranker_top_k: rerankerTopK,
            retriever_top_k: retrieverTopK,
            refinement_iterations: refinementIterations,
        };

        const response = await fetch(`${API_BASE_URL}/research`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestPayload),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        displayResults(data);
        hideLoading();
    } catch (error) {
        console.error('Search error:', error);
        showError(`Failed to process query: ${error.message}`);
        hideLoading();
    } finally {
        disableSearchButton(false);
    }
}

/**
 * Display search results
 */
function displayResults(data) {
    // Hide error section if shown
    errorSection.classList.add('hidden');

    // Answer
    const answerContent = document.getElementById('answerContent');
    answerContent.innerHTML = formatMarkdown(data.answer);

    // Confidence badge
    const confidenceBadge = document.getElementById('confidenceBadge');
    const confidence = (data.confidence * 100).toFixed(1);
    confidenceBadge.textContent = `Confidence: ${confidence}%`;
    confidenceBadge.style.background = getConfidenceColor(data.confidence);

    // Metrics
    const criticFeedback = data.critic_feedback || {};

    updateMetric(
        'factualScore',
        'factualBar',
        criticFeedback.factual_correctness_score
    );
    updateMetric(
        'completenessScore',
        'completenessBar',
        criticFeedback.completeness_score
    );
    updateMetric(
        'qualityScore',
        'qualityBar',
        criticFeedback.overall_quality
    );
    updateMetric(
        'hallucScore',
        'hallucBar',
        criticFeedback.hallucination_risk
    );

    // Sources
    displaySources(data.sources || []);

    // Feedback
    displayFeedback(criticFeedback);

    // Metadata
    document.getElementById('elapsedTime').textContent = `${data.elapsed_seconds?.toFixed(2) || '--'}s`;
    document.getElementById('iterationsRun').textContent = data.refinement_iterations_run || 0;

    // Errors
    if (data.pipeline_errors && data.pipeline_errors.length > 0) {
        document.getElementById('errorRow').classList.remove('hidden');
        document.getElementById('errorsList').textContent = data.pipeline_errors.join(', ');
    } else {
        document.getElementById('errorRow').classList.add('hidden');
    }

    // Show results section
    resultsSection.classList.remove('hidden');
    scrollToResults();
}

/**
 * Update metric display
 */
function updateMetric(scoreId, barId, value) {
    const scoreEl = document.getElementById(scoreId);
    const barEl = document.getElementById(barId);

    if (value !== undefined && value !== null) {
        const percentage = (value * 100).toFixed(0);
        scoreEl.textContent = `${percentage}%`;
        barEl.style.width = `${percentage}%`;
    } else {
        scoreEl.textContent = '--';
        barEl.style.width = '0%';
    }
}

/**
 * Display sources with proper formatting
 */
function displaySources(sources) {
    const sourcesList = document.getElementById('sourcesList');
    const sourceCount = document.getElementById('sourceCount');

    sourcesList.innerHTML = '';
    sourceCount.textContent = `${sources.length} source${sources.length !== 1 ? 's' : ''}`;

    sources.forEach((url, index) => {
        const item = document.createElement('div');
        item.className = 'source-item';

        const domain = extractDomain(url);

        item.innerHTML = `
            <div class="source-index">${index + 1}</div>
            <div class="source-url">
                <a href="${url}" target="_blank" rel="noopener noreferrer" class="source-link">
                    ${truncateUrl(url, 80)}
                </a>
                <span class="source-domain">${domain}</span>
            </div>
        `;

        sourcesList.appendChild(item);
    });
}

/**
 * Display critic feedback
 */
function displayFeedback(feedback) {
    const feedbackSection = document.getElementById('feedbackSection');
    const feedbackContent = document.getElementById('feedbackContent');

    const hasFeedback =
        (feedback.missing_information && feedback.missing_information.length > 0) ||
        (feedback.improvement_suggestions && feedback.improvement_suggestions.length > 0);

    if (!hasFeedback) {
        feedbackSection.classList.add('hidden');
        return;
    }

    feedbackSection.classList.remove('hidden');
    feedbackContent.innerHTML = '';

    if (feedback.missing_information && feedback.missing_information.length > 0) {
        const item = document.createElement('div');
        item.className = 'feedback-item';
        item.innerHTML = `
            <div class="feedback-item-title">Missing Information</div>
            <div class="feedback-item-text">
                ${feedback.missing_information.join('; ')}
            </div>
        `;
        feedbackContent.appendChild(item);
    }

    if (feedback.improvement_suggestions && feedback.improvement_suggestions.length > 0) {
        feedback.improvement_suggestions.forEach((suggestion) => {
            const item = document.createElement('div');
            item.className = 'feedback-item';
            item.innerHTML = `
                <div class="feedback-item-title">Suggestion</div>
                <div class="feedback-item-text">${suggestion}</div>
            `;
            feedbackContent.appendChild(item);
        });
    }
}

/**
 * Show loading state with step indicators
 */
function showLoading() {
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    loadingSection.classList.remove('hidden');

    // Reset steps
    STEPS.forEach((stepId) => {
        document.getElementById(stepId).classList.remove('active');
    });

    // Start animating steps
    let currentStep = 0;
    const stepInterval = setInterval(() => {
        if (currentStep > 0) {
            document.getElementById(STEPS[currentStep - 1]).classList.remove('active');
        }
        if (currentStep < STEPS.length) {
            document.getElementById(STEPS[currentStep]).classList.add('active');
            currentStep++;
        } else {
            clearInterval(stepInterval);
        }
    }, 1500);
}

/**
 * Hide loading state
 */
function hideLoading() {
    loadingSection.classList.add('hidden');
}

/**
 * Show error message
 */
function showError(message) {
    resultsSection.classList.add('hidden');
    loadingSection.classList.add('hidden');
    errorSection.classList.remove('hidden');
    document.getElementById('errorMessage').textContent = message;
}

/**
 * Disable/enable search button
 */
function disableSearchButton(disabled) {
    searchBtn.disabled = disabled;
    if (disabled) {
        spinner.classList.remove('hidden');
        document.querySelector('.button-text').textContent = 'Searching...';
    } else {
        spinner.classList.add('hidden');
        document.querySelector('.button-text').textContent = 'Search';
    }
}

/**
 * Scroll to results section
 */
function scrollToResults() {
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Format markdown-like content (basic implementation)
 */
function formatMarkdown(text) {
    if (!text) return '';

    let html = text
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.*?)__/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/_(.*?)_/g, '<em>$1</em>')
        // Links
        .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
        // Line breaks
        .replace(/\n/g, '<br>');

    return html;
}

/**
 * Extract domain from URL
 */
function extractDomain(url) {
    try {
        const urlObj = new URL(url);
        return urlObj.hostname;
    } catch {
        return url;
    }
}

/**
 * Truncate URL for display
 */
function truncateUrl(url, maxLength) {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
}

/**
 * Get color based on confidence score
 */
function getConfidenceColor(confidence) {
    if (confidence >= 0.8) return '#10b981'; // Green
    if (confidence >= 0.6) return '#f59e0b'; // Amber
    return '#ef4444'; // Red
}

/**
 * Initialize on DOM ready
 */
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();

    // Auto-focus search input
    queryInput.focus();

    // Set focus on search input when page loads
    setTimeout(() => queryInput.focus(), 100);
});

/**
 * Handle page unload for cleanup
 */
window.addEventListener('beforeunload', () => {
    // Could add cleanup logic here if needed
});
