from flask import Flask, render_template, request, jsonify
import pandas as pd
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from datetime import datetime
import os

# NLTK setup
nltk.download('punkt')
nltk.download('stopwords')

app = Flask(__name__)

# File paths
book_file_name = "books_data.csv"
borrower_file_name = "borrowers_data.csv"

# Load book data
if not os.path.exists(book_file_name):
    books_data = pd.DataFrame(columns=['isbn13', 'title', 'author', 'categories', 'average_rating', 'thumbnail'])
else:
    try:
        books_data = pd.read_csv(book_file_name)
    except Exception as e:
        books_data = pd.DataFrame(columns=['isbn13', 'title', 'author', 'categories', 'average_rating', 'thumbnail'])
        print(f"Error loading books dataset: {e}")

# Load borrower data
if not os.path.exists(borrower_file_name):
    borrower_data = pd.DataFrame(columns=['borrower_id', 'book_id', 'title', 'borrower_name', 'borrower_email', 'borrowed_date', 'returned'])
else:
    try:
        borrower_data = pd.read_csv(borrower_file_name)
        # Ensure the 'returned' column exists, if not, create it
        if 'returned' not in borrower_data.columns:
            borrower_data['returned'] = False
    except Exception as e:
        borrower_data = pd.DataFrame(columns=['borrower_id', 'book_id', 'title', 'borrower_name', 'borrower_email', 'borrowed_date', 'returned'])
        print(f"Error loading borrower dataset: {e}")


# Function to preprocess text for search functionality
def preprocess_text(text):
    tokens = word_tokenize(text.lower())
    filtered_tokens = [word for word in tokens if word.isalnum() and word not in stopwords.words('english')]
    return ' '.join(filtered_tokens)

# Home route for book search
@app.route('/', methods=['GET', 'POST'])
def home():
    search_results = []
    if request.method == 'POST':
        query = request.form.get('query')
        if query:  # Ensure query is not None or empty
            processed_query = preprocess_text(query)
            
            filtered_books = books_data[
                books_data['title'].apply(lambda x: processed_query in preprocess_text(str(x))) |
                books_data['author'].apply(lambda x: processed_query in preprocess_text(str(x)))
            ]
            
            search_results = filtered_books[['isbn13', 'title', 'author', 'categories', 'average_rating', 'thumbnail']].dropna().to_dict(orient='records')
        else:
            search_results.append({'error': 'Search query is empty.'})
    
    return render_template('index.html', results=search_results)

# Borrow route
@app.route('/borrow/<isbn13>', methods=['POST'])
def borrow(isbn13):
    global borrower_data  # Use the global borrower_data variable

    # Retrieve form data
    name = request.form.get('name')
    email = request.form.get('email')

    if not name or not email:
        return jsonify({"error": "Missing borrower details"}), 400

    # Find book details for the given isbn13
    book_details = books_data[books_data['isbn13'].astype(str) == isbn13].iloc[0] if not books_data[books_data['isbn13'].astype(str) == isbn13].empty else None

    if book_details is None:
        return jsonify({"error": "Book not found"}), 400

    if borrower_data.empty:
        borrower_id = 1
    else:
        last_id = borrower_data['borrower_id'].max()
        borrower_id = int(last_id) + 1 if not pd.isna(last_id) else 1

    new_borrowed_book = {
        'borrower_id': borrower_id,
        'book_id': isbn13,
        'title': book_details['title'],
        'borrower_name': name,
        'borrower_email': email,
        'borrowed_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'returned': False  # New column to track return status
    }

    # Append the new entry to borrower_data
    borrower_data = pd.concat([borrower_data, pd.DataFrame([new_borrowed_book])], ignore_index=True)

    # Save updated data to CSV
    try:
        borrower_data.to_csv(borrower_file_name, index=False)
    except Exception as e:
        return jsonify({"error": f"Error saving borrower data to CSV: {e}"}), 500

    # Return JSON response with the new borrowed book entry and success message
    return jsonify({"message": "Book borrowed successfully", "book": new_borrowed_book}), 200

# Borrowed Books route
@app.route('/borrowed_books')
def borrowed_books_view():
    return render_template('borrowed_books.html', borrowed_books=borrower_data[borrower_data['returned'] == False].to_dict(orient='records'))

if __name__ == '__main__':
    app.run(debug=True)
