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
    // Citation click handler for scroll and pulse effect
    document.addEventListener('click', handleCitationClick);
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

        const response = await fetch(`${API_BASE_URL}/research/stream`, {
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

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalData = null;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Hold onto incomplete line

            for (const line of lines) {
                const cleanLine = line.trim();
                if (cleanLine.startsWith('data: ')) {
                    const dataStr = cleanLine.slice(6);
                    if (dataStr.trim()) {
                        try {
                            const parsedEvent = JSON.parse(dataStr);
                            handleStreamEvent(parsedEvent);
                            if (parsedEvent.event === 'result') {
                                finalData = parsedEvent.data;
                            }
                        } catch (err) {
                            console.error('SSE line parse error:', err);
                        }
                    }
                }
            }
        }

        if (finalData) {
            displayResults(finalData);
            hideLoading();
        } else {
            throw new Error('Pipeline completed without returning final results.');
        }
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
    answerContent.innerHTML = formatMarkdown(data.answer, data.source_details);

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

    // Sources (use structured source details if available)
    displaySources(data.source_details || data.sources || []);

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

    sources.forEach((src, index) => {
        const item = document.createElement('div');
        item.className = 'source-item';

        let url = '';
        let title = '';
        let domain = '';

        if (typeof src === 'string') {
            url = src;
            title = truncateUrl(url, 80);
            domain = extractDomain(url);
        } else {
            url = src.url;
            title = src.title || truncateUrl(url, 80);
            domain = src.domain || extractDomain(url);
        }

        item.innerHTML = `
            <div class="source-index">${index + 1}</div>
            <div class="source-url">
                <a href="${url}" target="_blank" rel="noopener noreferrer" class="source-link">
                    ${title}
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

    // Clear console
    const consoleBody = document.getElementById('consoleBody');
    if (consoleBody) {
        consoleBody.innerHTML = '<div class="console-line info">Connecting to agent swarm...</div>';
    }
    document.getElementById('consoleStatus').textContent = 'CONNECTING...';
}

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
function formatMarkdown(text, sourceDetails) {
    if (!text) return '';

    // Create lookup map of URLs for citations
    const urlMap = {};
    if (sourceDetails && sourceDetails.length > 0) {
        sourceDetails.forEach((src, idx) => {
            urlMap[src.url] = {
                index: idx + 1,
                title: src.title,
                domain: src.domain
            };
        });
    }

    let html = text;

    // 1. Replace [Source: URL] citations with elegant badges
    const citationRegex = /\[Source:\s*(https?:\/\/[^\s\]>\"']+)(?:\s+.*?)*\]/g;
    html = html.replace(citationRegex, (match, url) => {
        const info = urlMap[url];
        if (info) {
            return `<a class="citation-badge" href="${url}" target="_blank" data-url="${url}" title="${info.title} (${info.domain})">[${info.index}]</a>`;
        }
        return `<a class="citation-badge" href="${url}" target="_blank" data-url="${url}" title="${url}">[Link]</a>`;
    });

    // 2. Standard markdown links [text](url)
    html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    // 3. Headings
    html = html
        .replace(/^### (.*?)$/gm, '<h3>$1</h3>')
        .replace(/^## (.*?)$/gm, '<h2>$1</h2>')
        .replace(/^# (.*?)$/gm, '<h1>$1</h1>');

    // 4. Bold and Italic
    html = html
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.*?)__/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/_(.*?)_/g, '<em>$1</em>');

    // 5. Unordered list bullet items
    html = html.replace(/^\s*[\*\-]\s+(.*?)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*?<\/li>)+/g, '<ul>$&</ul>');

    // 6. Ordered list items
    html = html.replace(/^\s*\d+\.\s+(.*?)$/gm, '<li class="ordered-list-item">$1</li>');
    html = html.replace(/(<li class="ordered-list-item">.*?<\/li>)+/g, '<ol>$&</ol>');
    html = html.replaceAll('class="ordered-list-item"', '');

    // 7. Paragraph blocks (group lines by double-newlines)
    const blocks = html.split(/\n{2,}/);
    const parsedBlocks = blocks.map(block => {
        const trimmed = block.trim();
        if (!trimmed) return '';
        if (trimmed.startsWith('<h') || trimmed.startsWith('<ul') || trimmed.startsWith('<ol') || trimmed.startsWith('<li')) {
            return trimmed;
        }
        return `<p>${trimmed.replace(/\n/g, '<br>')}</p>`;
    });
    html = parsedBlocks.join('\n');

    return html;
}

/**
 * Handle real-time Server-Sent Events from research stream
 */
function handleStreamEvent(event) {
    if (event.event === 'start') {
        const consoleBody = document.getElementById('consoleBody');
        if (consoleBody) consoleBody.innerHTML = '';
        writeConsoleLog(event.message, 'info');
        document.getElementById('consoleStatus').textContent = 'ACTIVE';
    } else if (event.event === 'progress') {
        writeConsoleLog(event.message, 'info');
        updateLoaderStep(event.node);
        
        // Output specific critic details if critique is complete
        if (event.node === 'critique' && event.details && event.details.overall_quality !== undefined) {
            const d = event.details;
            writeConsoleLog(`Critic Stats - Factual Quality: ${Math.round(d.factual_correctness*100)}% | Completeness: ${Math.round(d.completeness*100)}% | Hallucination Risk: ${Math.round(d.hallucination_risk*100)}%`, 'success');
            
            if (d.improvement_suggestions && d.improvement_suggestions.length > 0) {
                d.improvement_suggestions.forEach(s => {
                    writeConsoleLog(`Critic Suggestion: ${s}`, 'warn');
                });
            }
        }
    } else if (event.event === 'error') {
        writeConsoleLog(event.message, 'error');
        showError(event.message);
        document.getElementById('consoleStatus').textContent = 'ERROR';
    } else if (event.event === 'result') {
        writeConsoleLog('Pipeline finished execution. Synthesis complete!', 'success');
        document.getElementById('consoleStatus').textContent = 'DONE';
    }
}

/**
 * Update step loader visual states
 */
function updateLoaderStep(nodeName) {
    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    const step3 = document.getElementById('step3');
    const step4 = document.getElementById('step4');
    
    if (!step1 || !step2 || !step3 || !step4) return;
    
    // Clear active
    [step1, step2, step3, step4].forEach(el => el.classList.remove('active'));
    
    if (nodeName === 'search') {
        step1.classList.add('active');
    } else if (nodeName === 'rerank') {
        step1.classList.add('active');
        step2.classList.add('active');
    } else if (nodeName === 'read' || nodeName === 'chunk' || nodeName === 'embed') {
        step1.classList.add('active');
        step2.classList.add('active');
        step3.classList.add('active');
    } else if (nodeName === 'retrieve' || nodeName === 'write' || nodeName === 'critique' || nodeName === 'finalise') {
        step1.classList.add('active');
        step2.classList.add('active');
        step3.classList.add('active');
        step4.classList.add('active');
    }
}

/**
 * Append message line to Live Agent Console
 */
function writeConsoleLog(message, type = 'info') {
    const consoleBody = document.getElementById('consoleBody');
    if (!consoleBody) return;
    
    const line = document.createElement('div');
    line.className = `console-line ${type}`;
    line.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
    consoleBody.appendChild(line);
    
    // Scroll wrapper to bottom
    const consoleWrapper = consoleBody.parentElement;
    if (consoleWrapper) {
        consoleWrapper.scrollTop = consoleWrapper.scrollHeight;
    }
}

/**
 * Scroll and trigger pulse animation for clicked citation source card
 */
function handleCitationClick(e) {
    const badge = e.target.closest('.citation-badge');
    if (badge) {
        e.preventDefault();
        const url = badge.getAttribute('data-url');
        if (url) {
            const sourceItems = document.querySelectorAll('.source-item');
            let targetItem = null;
            sourceItems.forEach(item => {
                const link = item.querySelector('.source-link');
                if (link && link.href === url) {
                    targetItem = item;
                }
            });
            
            if (targetItem) {
                targetItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                // Reset any existing animations
                targetItem.classList.remove('highlighted');
                void targetItem.offsetWidth; // Force reflow
                targetItem.classList.add('highlighted');
                
                // Clear highlighted class after a few seconds
                setTimeout(() => {
                    targetItem.classList.remove('highlighted');
                }, 3000);
            } else {
                window.open(url, '_blank');
            }
        }
    }
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
