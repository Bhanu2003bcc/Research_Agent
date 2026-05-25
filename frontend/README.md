# Multi-Agent Research System - Frontend UI

A professional, interactive web interface for the multi-agent research system.

## Overview

The frontend provides a modern, responsive UI for:
- Submitting research queries
- Real-time progress tracking
- Viewing detailed results with citations
- Quality metrics and confidence scores
- Critic feedback and suggestions

## Features

### Search Interface
- Clean, intuitive search bar
- Customizable pipeline parameters:
  - Search Results (top-n)
  - Reranker Top K
  - Retriever Top K
  - Refinement Iterations

### Results Display
- **Answer Section**: Formatted answer with inline citations
- **Quality Metrics**: Visual indicators for:
  - Factual Correctness
  - Completeness
  - Overall Quality
  - Hallucination Risk
- **Sources**: Clickable source links with domain information
- **Feedback**: Improvement suggestions from the critic agent
- **Metadata**: Processing time and iteration count

### User Experience
- Real-time loading with step indicators
- Error handling with detailed messages
- Responsive design for mobile and desktop
- Smooth animations and transitions
- Accessibility-focused design

## File Structure

```
frontend/
├── index.html       # Main HTML template
├── styles.css       # Professional styling (no framework)
└── script.js        # API integration and UI logic
```

## Technologies

- **HTML5**: Semantic markup
- **CSS3**: Custom properties, Grid, Flexbox, responsive design
- **Vanilla JavaScript**: No dependencies, Fetch API for backend communication
- **FastAPI Integration**: RESTful API communication

## Styling

The UI uses a modern color palette with:
- Primary: Blue (#2563eb)
- Secondary: Purple (#7c3aed)
- Success: Green (#10b981)
- Warning: Amber (#f59e0b)
- Danger: Red (#ef4444)

All typography and spacing use CSS custom properties for consistency and easy theming.

## API Integration

The frontend communicates with the backend via the `/research` endpoint:

```javascript
POST /research
Content-Type: application/json

{
  "query": "Your research query",
  "search_top_n": 10,
  "reranker_top_k": 5,
  "retriever_top_k": 8,
  "refinement_iterations": 2
}
```

## Browser Support

- Chrome/Chromium (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Development

The frontend requires no build step. Simply:

1. Start the FastAPI server: `python main.py`
2. Visit `http://localhost:8000` in your browser
3. The UI will automatically load and connect to the backend API

## Customization

### Colors
Edit CSS custom properties in `styles.css` (`:root` section):

```css
--primary-color: #2563eb;
--secondary-color: #7c3aed;
/* etc. */
```

### Typography
Modify font families and sizes in the `:root` section:

```css
--font-family: /* your font stack */;
--font-size-base: 1rem;
/* etc. */
```

### Layout
Adjust spacing and breakpoints as needed:

```css
--spacing-xl: 2rem;
/* etc. */
```

## Performance

- **Lightweight**: ~8KB HTML + CSS + JS (minified)
- **No external dependencies**: Uses browser APIs only
- **Optimized animations**: GPU-accelerated with CSS transforms
- **Responsive images**: Optimized for all screen sizes

## Accessibility

- Semantic HTML structure
- ARIA labels where needed
- Keyboard navigation support
- Focus indicators for all interactive elements
- Color contrast meets WCAG AA standards

## Error Handling

The UI gracefully handles:
- Network errors
- API timeouts
- Invalid parameters
- Pipeline failures

Users see clear error messages and recovery options.

## Future Enhancements

Possible improvements:
- Export results (PDF/JSON)
- Search history
- Saved queries
- Advanced filtering
- Result comparison
- Dark mode
- Multi-language support
