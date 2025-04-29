from flask import Flask, render_template, request, jsonify, abort
import os
from pathlib import Path
from search_engine import BooleanSearchEngine

app = Flask(__name__, static_folder='static', template_folder='templates')

# Use relative paths
BASE_DIR = Path(__file__).parent
INDEX_DIR = BASE_DIR / "index_files"
index_path = INDEX_DIR / "inverted_index.json"
metadata_path = INDEX_DIR / "document_metadata.json"

# Initialize search engine
try:
    if not index_path.exists() or not metadata_path.exists():
        raise FileNotFoundError("Index files not found. Please run build_index.py first.")
    search_engine = BooleanSearchEngine(str(index_path), str(metadata_path))
except Exception as e:
    print(f"Error initializing search engine: {e}")
    search_engine = None

@app.route('/')
def home():
    """Render the search homepage."""
    return render_template('index.html')

@app.route('/search')
def search():
    """Handle search requests."""
    if not search_engine:
        return render_template('error.html', error="Search engine not initialized. Please check index files.")
    
    query = request.args.get('q', '').strip()
    
    if not query:
        return render_template('index.html')
    
    try:
        results = search_engine.search(query)
        return render_template('results.html', query=query, results=results)
    except Exception as e:
        print(f"Search error: {e}")
        return render_template('error.html', error=str(e))

@app.route('/document/<int:doc_id>')
def document(doc_id):
    """Display a specific document."""
    if not search_engine:
        return render_template('error.html', error="Search engine not initialized.")
    
    try:
        doc = search_engine.get_document(doc_id)
        if doc:
            return render_template('document.html', document=doc)
        else:
            abort(404)
    except Exception as e:
        print(f"Document retrieval error: {e}")
        abort(500)

@app.route('/api/search')
def api_search():
    """API endpoint for search."""
    if not search_engine:
        return jsonify({'error': 'Search engine not initialized'}), 500
    
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        results = search_engine.search(query)
        return jsonify({'query': query, 'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/document/<int:doc_id>')
def api_document(doc_id):
    """API endpoint for document retrieval."""
    if not search_engine:
        return jsonify({'error': 'Search engine not initialized'}), 500
    
    try:
        doc = search_engine.get_document(doc_id)
        if doc:
            return jsonify(doc)
        else:
            return jsonify({'error': 'Document not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/autocomplete')
def api_autocomplete():
    """API endpoint for autocomplete suggestions."""
    if not search_engine:
        return jsonify({'error': 'Search engine not initialized'}), 500
    
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify([])
    
    try:
        suggestions = [
            term for term in search_engine.inverted_index.get('any', {})
            if term.startswith(query)
        ][:5]
        return jsonify(suggestions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/help')
def help_page():
    """Display help information."""
    return render_template('help.html')

if __name__ == '__main__':
    app.run(debug=True)