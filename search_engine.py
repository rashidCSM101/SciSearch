import json
import re
from typing import List, Dict, Set, Union, Any
import os

class BooleanSearchEngine:
    """
    Search engine implementing Boolean model for scientific papers.
    Supports AND, OR, NOT operators, field-specific searching, and phrase searches.
    """
    
    def __init__(self, index_path: str, metadata_path: str):
        """
        Initialize search engine with index and metadata files.
        
        Args:
            index_path: Path to inverted index JSON file
            metadata_path: Path to document metadata JSON file
        """
        try:
            # Load inverted index
            with open(index_path, 'r', encoding='utf-8') as f:
                self.inverted_index = json.load(f)
            
            # Convert document IDs to integers
            for field in self.inverted_index:
                for term, doc_ids in self.inverted_index[field].items():
                    self.inverted_index[field][term] = [int(doc_id) for doc_id in doc_ids]
            
            # Load document metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.doc_metadata = json.load(f)
            
            # Convert metadata keys to integers
            self.doc_metadata = {int(doc_id): data for doc_id, data in self.doc_metadata.items()}
            
            # Get set of all document IDs
            self.all_doc_ids = set(self.doc_metadata.keys())
            
            print(f"Loaded index with {sum(len(terms) for terms in self.inverted_index.values())} terms and {len(self.doc_metadata)} documents")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in index files: {e}")
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Index file not found: {e}")
    
    def preprocess_query(self, query: str) -> str:
        """
        Preprocess query by converting to lowercase.
        
        Args:
            query: User's search query
            
        Returns:
            Preprocessed query
        """
        return query.lower().strip()
    
    def parse_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Parse a query into a structured format.
        
        Args:
            query: User's search query
            
        Returns:
            List of dictionaries representing query components
        """
        # Replace Boolean operators with placeholders
        query = re.sub(r'\bAND\b', ' & ', query)
        query = re.sub(r'\bOR\b', ' | ', query)
        query = re.sub(r'\bNOT\b', ' ! ', query)
        
        # Split by spaces while preserving quoted phrases
        tokens = []
        current_token = ""
        in_quotes = False
        
        for char in query:
            if char == '"':
                in_quotes = not in_quotes
                current_token += char
            elif char == ' ' and not in_quotes:
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
            else:
                current_token += char
        
        if current_token:
            tokens.append(current_token)
        
        # Parse tokens into structured query
        parsed_query = []
        current_operator = '|'  # Default to OR
        
        for token in tokens:
            if token in ('&', '|'):
                current_operator = token
            elif token == '!':
                parsed_query.append({'type': 'NOT'})
            elif token.startswith('"') and token.endswith('"') and len(token) > 2:
                # Phrase search
                phrase = token[1:-1]
                parsed_query.append({
                    'type': 'PHRASE',
                    'field': 'any',
                    'phrase': phrase,
                    'operator': current_operator
                })
            elif ':' in token and not in_quotes:
                # Field search
                try:
                    field, term = token.split(':', 1)
                    if term.startswith('"') and term.endswith('"'):
                        term = term[1:-1]
                        parsed_query.append({
                            'type': 'PHRASE',
                            'field': field,
                            'phrase': term,
                            'operator': current_operator
                        })
                    else:
                        parsed_query.append({
                            'type': 'TERM',
                            'field': field,
                            'term': term,
                            'operator': current_operator
                        })
                except ValueError:
                    continue
            else:
                # Regular term search
                if token.startswith('"') and token.endswith('"'):
                    token = token[1:-1]
                parsed_query.append({
                    'type': 'TERM',
                    'field': 'any',
                    'term': token,
                    'operator': current_operator
                })
        
        return parsed_query
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for documents matching the query.
        
        Args:
            query: User's search query
            
        Returns:
            List of document metadata matching the query
        """
        if not query:
            return []
        
        # Preprocess and parse the query
        query = self.preprocess_query(query)
        parsed_query = self.parse_query(query)
        
        if not parsed_query:
            return []
        
        # Execute the search
        result_set = self._execute_query(parsed_query)
        
        # Get metadata for matching documents
        results = []
        for doc_id in result_set:
            if doc_id in self.doc_metadata:
                doc_data = self.doc_metadata[doc_id].copy()
                doc_data['doc_id'] = doc_id
                results.append(doc_data)
        
        # Sort results by document ID (can be improved with relevance ranking)
        results.sort(key=lambda x: x['doc_id'])
        
        return results
    
    def _execute_query(self, parsed_query: List[Dict[str, Any]]) -> Set[int]:
        """
        Execute the parsed query and return matching document IDs.
        
        Args:
            parsed_query: Parsed query components
            
        Returns:
            Set of document IDs matching the query
        """
        result_set = set()
        apply_not = False
        
        for i, component in enumerate(parsed_query):
            if component['type'] == 'NOT':
                apply_not = True
                continue
            
            term_docs = set()
            
            if component['type'] == 'TERM':
                term = component['term']
                field = component['field']
                
                if field == 'any':
                    if term in self.inverted_index.get('any', {}):
                        term_docs = set(self.inverted_index['any'][term])
                else:
                    if term in self.inverted_index.get(field, {}):
                        term_docs = set(self.inverted_index[field][term])
            
            elif component['type'] == 'PHRASE':
                phrase = component['phrase']
                field = component['field']
                term_docs = self._execute_phrase_query(phrase, field)
            
            # Apply NOT operator
            if apply_not:
                term_docs = self.all_doc_ids - term_docs
                apply_not = False
            
            # Apply Boolean operator
            if i == 0 or component['operator'] == '|':
                result_set = result_set.union(term_docs)
            elif component['operator'] == '&':
                result_set = result_set.intersection(term_docs)
        
        return result_set
    
    def _execute_phrase_query(self, phrase: str, field: str) -> Set[int]:
        """
        Execute a phrase query, ensuring terms appear consecutively.
        
        Args:
            phrase: Phrase to search for
            field: Field to search in ('any' or specific field)
            
        Returns:
            Set of document IDs where the phrase appears
        """
        terms = phrase.lower().split()
        if not terms:
            return set()
        
        # Get documents containing all terms
        doc_sets = []
        for term in terms:
            if field == 'any':
                if term in self.inverted_index.get('any', {}):
                    doc_sets.append(set(self.inverted_index['any'][term]))
            else:
                if term in self.inverted_index.get(field, {}):
                    doc_sets.append(set(self.inverted_index[field][term]))
        
        common_docs = set.intersection(*doc_sets) if doc_sets else set()
        
        # Verify phrase by checking positions
        result_docs = set()
        for doc_id in common_docs:
            positions = []
            for term in terms:
                pos_list = self.inverted_index.get(field, {}).get(term, {}).get(str(doc_id), [])
                positions.append(pos_list)
            
            # Check for consecutive positions
            for pos in positions[0]:
                if all(pos + i in positions[i] for i in range(1, len(terms))):
                    result_docs.add(doc_id)
                    break
        
        return result_docs
    
    def get_document(self, doc_id: int) -> Dict[str, Any]:
        """
        Get full metadata for a specific document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document metadata or None if not found
        """
        doc_id = int(doc_id)
        if doc_id in self.doc_metadata:
            result = self.doc_metadata[doc_id].copy()
            result['doc_id'] = doc_id
            return result
        return None

def main():
    # Example usage
    from pathlib import Path
    BASE_DIR = Path(__file__).parent
    index_path = BASE_DIR / "index_files" / "inverted_index.json"
    metadata_path = BASE_DIR / "index_files" / "document_metadata.json"
    
    try:
        search_engine = BooleanSearchEngine(str(index_path), str(metadata_path))
        query = "machine AND learning"
        results = search_engine.search(query)
        
        print(f"Search results for '{query}':")
        for result in results:
            print(f"Document {result['doc_id']}: {result['title']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()