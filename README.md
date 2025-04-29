# Information Retrieval System

A powerful Boolean search engine for scientific papers with advanced features including spell correction, document viewing, and multi-operator search capabilities.

## Features

- **Boolean Search**: Use AND, OR, NOT operators to create precise search queries
- **Spell Correction**: Automatic suggestions for misspelled search terms
- **Advanced Search Interface**: Separate fields for AND, OR, NOT operators
- **PDF Viewing**: View scientific papers directly in your browser
- **Document Information Panel**: ChatGPT-like information display for documents
- **Responsive Design**: Works on all devices and screen sizes

## Technologies Used

- Flask web framework
- Python for backend logic
- HTML, CSS, and JavaScript for frontend
- Custom search engine with Boolean operators
- Levenshtein distance for spell correction

## Deployment Instructions

### Local Development

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python app_with_spell_correction.py
   ```
4. Open http://localhost:5000 in your browser

### Production Deployment

This application can be deployed to various platforms:

#### Heroku

1. Create a Heroku account and install the Heroku CLI
2. Login to Heroku:
   ```
   heroku login
   ```
3. Create a new Heroku app:
   ```
   heroku create your-app-name
   ```
4. Push to Heroku:
   ```
   git push heroku main
   ```

#### PythonAnywhere

1. Create a PythonAnywhere account
2. Upload your code to PythonAnywhere
3. Set up a web app with Flask
4. Configure your WSGI file to point to your Flask application

#### Render

1. Create a Render account
2. Connect your GitHub repository
3. Create a new Web Service
4. Select Python as the environment
5. Set the build command: `pip install -r requirements.txt`
6. Set the start command: `gunicorn app_with_spell_correction:app`

## Credits

Developed by Sayed Rashid Ali and Muhammad Usama Khan

© 2025 NovaTech and Usama-Rashid. All Rights Reserved.
