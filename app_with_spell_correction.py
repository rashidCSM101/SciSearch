from flask import Flask, render_template, request, jsonify, abort, send_from_directory
import os
from pathlib import Path
from search_engine_with_spell_correction import BooleanSearchEngine

app = Flask(__name__, static_folder='static', template_folder='templates')

# Use relative paths
BASE_DIR = Path(__file__).parent
INDEX_DIR = BASE_DIR / "index_files"
PDF_DIR = BASE_DIR / "PDFs 1-250"
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
    return render_template('index_final.html')

@app.route('/advanced_search')
def advanced_search():
    """Render the advanced search page."""
    # Get search parameters if they exist
    and_terms = request.args.get('and_terms', '')
    or_terms = request.args.get('or_terms', '')
    not_terms = request.args.get('not_terms', '')
    
    # If search parameters are provided, perform the search
    if and_terms or or_terms or not_terms:
        return perform_advanced_search(and_terms, or_terms, not_terms)
    
    # Otherwise just render the advanced search form
    return render_template('advanced_search_final.html', 
                          and_terms='', 
                          or_terms='', 
                          not_terms='')

def perform_advanced_search(and_terms, or_terms, not_terms):
    """Perform an advanced search with AND, OR, NOT operators."""
    if not search_engine:
        return render_template('error_final.html', error="Search engine not initialized. Please check index files.")
    
    try:
        # Construct the boolean query
        query_parts = []
        
        # Add AND terms
        if and_terms:
            and_terms_list = and_terms.strip().split()
            if len(and_terms_list) > 0:
                query_parts.append(" AND ".join(and_terms_list))
        
        # Add OR terms
        if or_terms:
            or_terms_list = or_terms.strip().split()
            if len(or_terms_list) > 0:
                query_parts.append("(" + " OR ".join(or_terms_list) + ")")
        
        # Add NOT terms
        if not_terms:
            not_terms_list = not_terms.strip().split()
            for term in not_terms_list:
                query_parts.append(f"NOT {term}")
        
        # Combine all parts with AND
        query = " AND ".join(query_parts) if query_parts else ""
        
        if not query:
            return render_template('advanced_search_final.html', 
                                  and_terms=and_terms, 
                                  or_terms=or_terms, 
                                  not_terms=not_terms)
        
        # Perform the search
        results = search_engine.search(query)
        
        # Check if spell correction was applied
        corrected_query = None
        if results and 'corrected_query' in results[0]:
            corrected_query = results[0]['corrected_query']
            original_query = results[0]['original_query']
            
            # Remove the correction info from results to keep them clean
            for result in results:
                if 'corrected_query' in result:
                    del result['corrected_query']
                if 'original_query' in result:
                    del result['original_query']
        
        return render_template('results_final.html', 
                              query=query, 
                              results=results, 
                              corrected_query=corrected_query,
                              and_terms=and_terms,
                              or_terms=or_terms,
                              not_terms=not_terms)
    except Exception as e:
        print(f"Advanced search error: {e}")
        return render_template('error_final.html', error=str(e))

@app.route('/search')
def search():
    """Handle search requests."""
    if not search_engine:
        return render_template('error_final.html', error="Search engine not initialized. Please check index files.")
    
    query = request.args.get('q', '').strip()
    
    if not query:
        return render_template('index_final.html')
    
    try:
        results = search_engine.search(query)
        
        # Check if spell correction was applied
        corrected_query = None
        if results and 'corrected_query' in results[0]:
            corrected_query = results[0]['corrected_query']
            original_query = results[0]['original_query']
            
            # Remove the correction info from results to keep them clean
            for result in results:
                if 'corrected_query' in result:
                    del result['corrected_query']
                if 'original_query' in result:
                    del result['original_query']
        
        return render_template('results_final.html', 
                              query=query, 
                              results=results, 
                              corrected_query=corrected_query)
    except Exception as e:
        print(f"Search error: {e}")
        return render_template('error_final.html', error=str(e))

@app.route('/document/<int:doc_id>')
def document(doc_id):
    """Display a specific document."""
    if not search_engine:
        return render_template('error_final.html', error="Search engine not initialized.")
    
    try:
        doc = search_engine.get_document(doc_id)
        if doc:
            return render_template('document_final.html', document=doc)
        else:
            abort(404)
    except Exception as e:
        print(f"Document retrieval error: {e}")
        abort(500)

@app.route('/view_pdf/<int:doc_id>')
def view_pdf(doc_id):
    """Serve the PDF file for a document."""
    try:
        # Check if the PDF exists
        pdf_path = f"{doc_id}.pdf"
        if not (PDF_DIR / pdf_path).exists():
            # If the exact PDF doesn't exist, return a 404
            return render_template('error_final.html', error=f"PDF file for document {doc_id} not found."), 404
        
        # Serve the PDF file
        return send_from_directory(PDF_DIR, pdf_path)
    except Exception as e:
        print(f"PDF retrieval error: {e}")
        return render_template('error_final.html', error=f"Error retrieving PDF: {str(e)}"), 500

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
        
        # Check if spell correction was applied
        corrected_query = None
        if results and 'corrected_query' in results[0]:
            corrected_query = results[0]['corrected_query']
            original_query = results[0]['original_query']
            
            # Remove the correction info from results to keep them clean
            for result in results:
                if 'corrected_query' in result:
                    del result['corrected_query']
                if 'original_query' in result:
                    del result['original_query']
                    
            return jsonify({
                'original_query': query,
                'corrected_query': corrected_query,
                'results': results
            })
        
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
            term for term in search_engine.all_terms
            if term.startswith(query)
        ][:5]
        return jsonify(suggestions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/help')
def help_page():
    """Display help information."""
    return render_template('help_final.html')

@app.route('/about')
def about_page():
    """Display about us page."""
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)
