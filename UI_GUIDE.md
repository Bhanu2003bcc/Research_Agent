# UI Setup & Usage Guide

## Quick Start

### 1. Restart Your Server

```bash
# Kill the current server (Ctrl+C in the terminal)
# Then start it again:
python main.py
```

### 2. Access the UI

Open your browser and navigate to:
```
http://localhost:8000
```

You'll see the new professional research interface!

## Using the Interface

### Search Section
1. **Enter Your Query**: Type your research question in the search box
2. **Configure Options** (optional):
   - **Search Results**: Number of initial Exa API results (1-50, default: 10)
   - **Reranker Top K**: Results kept after re-ranking (1-20, default: 5)
   - **Retriever Top K**: Chunks retrieved from FAISS (1-20, default: 8)
   - **Refinement Iterations**: Writer-Critic refinement loops (0-5, default: 2)
3. **Click Search**: Submit your query

### Results Display

Once the research completes, you'll see:

#### Answer Section
- **Professional Answer**: Formatted response with citations
- **Confidence Badge**: Color-coded reliability indicator
  - Green (80%+): High confidence
  - Amber (60-80%): Medium confidence
  - Red (<60%): Low confidence

#### Quality Metrics
Visual progress bars showing:
- **Factual Correctness**: How accurate the information is
- **Completeness**: How thoroughly the query is answered
- **Overall Quality**: Combined quality score
- **Hallucination Risk**: Likelihood of false information

#### Sources
- Numbered list of cited sources
- Clickable links to original content
- Domain name for quick reference
- Click any source to verify information

#### Improvement Suggestions
- AI-generated recommendations for better results
- Missing information gaps
- Areas needing more research

#### Processing Metadata
- **Processing Time**: How long the research took
- **Refinement Iterations**: Number of refinement loops run
- **Errors**: Any issues encountered (if any)

## Features

### Professional Design
- Clean, modern interface
- Gradient header with research branding
- Responsive layout (works on mobile, tablet, desktop)
- Smooth animations and transitions
- No emojis - maintains professionalism

### Real-Time Feedback
- Loading animation with step indicators
- Shows which stage of research is active
- Smooth transitions between states

### Error Handling
- Clear error messages
- Helpful recovery suggestions
- Professional error display

### No External Dependencies
- Pure HTML, CSS, and JavaScript
- Runs entirely in the browser
- No npm packages or build tools needed

## API Integration

The UI communicates directly with your FastAPI backend via:
- `POST /research` - Submit research queries
- `GET /health` - Check server status (optional)
- `GET /styles.css` - Load styling
- `GET /script.js` - Load functionality

## Customization

### Colors
Edit `frontend/styles.css` CSS variables:
```css
--primary-color: #2563eb;      /* Main blue */
--secondary-color: #7c3aed;    /* Purple */
--success-color: #10b981;      /* Green */
--warning-color: #f59e0b;      /* Amber */
--danger-color: #ef4444;       /* Red */
```

### Fonts
Modify font family in `styles.css`:
```css
--font-family: /* your font stack */;
```

### Spacing & Layout
Adjust in `styles.css`:
```css
--spacing-xl: 2rem;
--spacing-lg: 1.5rem;
/* etc. */
```

## Troubleshooting

### UI not loading?
1. Make sure the server is running: `python main.py`
2. Check the terminal for error messages
3. Verify frontend files exist in `frontend/` directory
4. Refresh your browser (Ctrl+R)

### Styling looks wrong?
1. Hard refresh your browser (Ctrl+Shift+R)
2. Clear browser cache
3. Check that `styles.css` is in the frontend directory

### Search button unresponsive?
1. Check browser console for JavaScript errors (F12)
2. Verify API is running (`curl http://localhost:8000/health`)
3. Check firewall settings

### Results not showing?
1. Check that your query is valid
2. Look at the error message displayed
3. Check server logs for details
4. Verify API key is set in `.env`

## Performance Tips

- Use specific, well-formed queries
- Start with default parameters
- Increase iterations only if needed
- Check source quality before citing

## Browser Support

Works best on:
- Chrome/Chromium (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## API Documentation

For advanced usage, access the Swagger UI:
```
http://localhost:8000/docs
```

This shows all available endpoints and parameters.

## Next Steps

- Customize colors and branding
- Integrate into your website
- Deploy to production
- Add additional features (export, history, etc.)

---

For more information, see `frontend/README.md`
