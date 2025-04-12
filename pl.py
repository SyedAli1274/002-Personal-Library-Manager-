import streamlit as st
import pandas as pd
import json
import os
import sqlite3
import requests
from PIL import Image
import io
import base64
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Configure the Streamlit page
st.set_page_config(
    page_title="Personal Library Manager",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)


load_dotenv()



# Add custom CSS for modern UI
st.markdown("""
<style>
    .main {
        padding: 1rem 2rem;
    }
    .book-card {
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
    }
    .book-card:hover {
        transform: translateY(-5px);
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .download-btn {
        background-color: #2196F3 !important;
    }
    .download-btn:hover {
        background-color: #0b7dda !important;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .sidebar-content {
        padding: 1.5rem 1rem;
    }
    h1, h2, h3 {
        color: #1E3A8A;
    }
    .section-divider {
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
# Modify the init_db function to ensure it adds exactly 3 sample books
def init_db():
    """Initialize SQLite database for book storage"""
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS books
        (id TEXT PRIMARY KEY,
         title TEXT NOT NULL,
         author TEXT NOT NULL,
         genre TEXT,
         description TEXT,
         published_year INTEGER,
         isbn TEXT,
         cover_image TEXT,
         date_added TEXT)
    ''')
    
    # Check if we have at least 3 books
    c.execute("SELECT COUNT(*) FROM books")
    count = c.fetchone()[0]
    
    # If we have fewer than 3 books, delete all and add exactly 3 sample books
    if count < 3:
        # Clear existing books to avoid duplicates
        c.execute("DELETE FROM books")
        
        # Add 3 sample books
        sample_books = [
            {
                'id': str(uuid.uuid4()),
                'title': 'Harry Potter and the Philosopher\'s Stone',
                'author': 'J.K. Rowling',
                'genre': 'Fantasy',
                'description': 'The first book in the Harry Potter series.',
                'published_year': 1997,
                'isbn': '9780590353427',
                'cover_image': 'https://via.placeholder.com/150?text=Harry+Potter',
                'date_added': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                'id': str(uuid.uuid4()),
                'title': 'To Kill a Mockingbird',
                'author': 'Harper Lee',
                'genre': 'Fiction',
                'description': 'A story about racial injustice and loss of innocence in the American South.',
                'published_year': 1960,
                'isbn': '9780061120084',
                'cover_image': 'https://via.placeholder.com/150?text=To+Kill+a+Mockingbird',
                'date_added': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                'id': str(uuid.uuid4()),
                'title': '1984',
                'author': 'George Orwell',
                'genre': 'Science Fiction',
                'description': 'A dystopian novel about totalitarianism and mass surveillance.',
                'published_year': 1949,
                'isbn': '9780451524935',
                'cover_image': 'https://via.placeholder.com/150?text=1984',
                'date_added': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
        
        for book in sample_books:
            c.execute('''
                INSERT INTO books (id, title, author, genre, description, published_year, isbn, cover_image, date_added)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                book['id'],
                book['title'],
                book['author'],
                book['genre'],
                book['description'],
                book['published_year'],
                book['isbn'],
                book['cover_image'],
                book['date_added']
            ))
    
    conn.commit()
    conn.close()


# Add this function to your code
def update_db_schema():
    """Update the database schema to include the file_path column if it doesn't exist"""
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    
    # Check if file_path column exists
    c.execute("PRAGMA table_info(books)")
    columns = [column[1] for column in c.fetchall()]
    
    # Add file_path column if it doesn't exist
    if 'file_path' not in columns:
        c.execute("ALTER TABLE books ADD COLUMN file_path TEXT")
        conn.commit()
        print("Added file_path column to database")
    
    conn.close()

# Call this function right after init_db()
init_db()
update_db_schema()

# Function to add a book to the database
def add_book_to_db(book_data):
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO books (id, title, author, genre, description, published_year, isbn, cover_image, date_added, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            book_data['id'],
            book_data['title'],
            book_data['author'],
            book_data['genre'],
            book_data['description'],
            book_data['published_year'],
            book_data['isbn'],
            book_data['cover_image'],
            book_data['date_added'],
            book_data.get('file_path', '')
        ))
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return False
    finally:
        conn.close()

# Function to get all books from the database
def get_all_books():
    conn = sqlite3.connect('library.db')
    books = pd.read_sql_query("SELECT * FROM books", conn)
    conn.close()
    return books

# Function to remove a book from the database
def remove_book(book_id):
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return False
    finally:
        conn.close()

# Function to search books by title or author
def search_books(query):
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    query = f"%{query}%"
    result = pd.read_sql_query(
        "SELECT * FROM books WHERE title LIKE ? OR author LIKE ?", 
        conn, 
        params=(query, query)
    )
    conn.close()
    return result

# Function to generate a download link for a book
def get_download_link(file_path, title):
    # Check if file exists
    if file_path and os.path.exists(file_path):
        # For a real file, read and encode it
        with open(file_path, "rb") as file:
            contents = file.read()
            b64 = base64.b64encode(contents).decode()
            ext = os.path.splitext(file_path)[1]
            return f'<a href="data:application/octet-stream;base64,{b64}" download="{title}{ext}">Download</a>'
    else:
        # Create sample content for demonstration
        if title == "Harry Potter and the Philosopher's Stone":
            sample_content = """
            HARRY POTTER AND THE PHILOSOPHER'S STONE
            by J.K. Rowling
            
            Chapter One: The Boy Who Lived
            
            Mr. and Mrs. Dursley, of number four, Privet Drive, were proud to say that they were perfectly normal, thank you very much. They were the last people you'd expect to be involved in anything strange or mysterious, because they just didn't hold with such nonsense.
            
            Mr. Dursley was the director of a firm called Grunnings, which made drills. He was a big, beefy man with hardly any neck, although he did have a very large mustache. Mrs. Dursley was thin and blonde and had nearly twice the usual amount of neck, which came in very useful as she spent so much of her time craning over garden fences, spying on the neighbors.
            
            This is a sample of the book content for demonstration purposes.
            """
        elif title == "To Kill a Mockingbird":
            sample_content = """
            TO KILL A MOCKINGBIRD
            by Harper Lee
            
            Chapter 1
            
            When he was nearly thirteen, my brother Jem got his arm badly broken at the elbow. When it healed, and Jem's fears of never being able to play football were assuaged, he was seldom self-conscious about his injury. His left arm was somewhat shorter than his right; when he stood or walked, the back of his hand was at right angles to his body, his thumb parallel to his thigh.
            
            This is a sample of the book content for demonstration purposes.
            """
        elif title == "1984":
            sample_content = """
            1984
            by George Orwell
            
            Part One
            
            Chapter 1
            
            It was a bright cold day in April, and the clocks were striking thirteen. Winston Smith, his chin nuzzled into his breast in an effort to escape the vile wind, slipped quickly through the glass doors of Victory Mansions, though not quickly enough to prevent a swirl of gritty dust from entering along with him.
            
            This is a sample of the book content for demonstration purposes.
            """
        else:
            sample_content = f"""
            {title}
            
            This is a sample preview of the book. In an actual implementation, this would contain the full text or a protected PDF version of the book.
            
            This file is a placeholder for demonstration purposes only.
            """
        
        # Create download link for the sample content
        b64 = base64.b64encode(sample_content.encode()).decode()
        return f'<a href="data:application/octet-stream;base64,{b64}" download="{title}.txt">Download</a>'
    


# Function to search for book information using Open Library API
def search_books_api(query):
    """Search for books using the Open Library API"""
    encoded_query = requests.utils.quote(query)
    url = f"https://openlibrary.org/search.json?q={encoded_query}&limit=3"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            books = []
            
            for doc in data.get('docs', [])[:3]:
                # Extract cover ID if available
                cover_id = doc.get('cover_i')
                cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else f"https://via.placeholder.com/150?text={doc.get('title', 'Book').replace(' ', '+')}"
                
                # Extract author names safely
                author_names = doc.get('author_name', ['Unknown Author'])
                author_text = ", ".join(author_names) if author_names else 'Unknown Author'
                
                # Extract subjects/genres safely
                subjects = doc.get('subject', [])
                genre_text = ", ".join(subjects[:2]) if subjects else 'Unspecified'
                
                # Create book entry
                book = {
                    "title": doc.get('title', 'Unknown Title'),
                    "author": author_text,
                    "genre": genre_text,
                    "description": f"A book by {author_text}. Published by {', '.join(doc.get('publisher', ['Unknown Publisher'])[:1])}.",
                    "published_year": doc.get('first_publish_year', 2000),
                    "isbn": ", ".join(doc.get('isbn', ['Unknown'])) if 'isbn' in doc else 'Unknown',
                    "cover_image": cover_url,
                    "file_path": ""  # No file available for API results initially
                }
                books.append(book)
            
            return books
        else:
            st.error(f"API Error: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)}")
        return []
   
# Initialize the app
init_db()

# Create sidebar for navigation
with st.sidebar:
    st.markdown("<div class='sidebar-content'>", unsafe_allow_html=True)
    image = Image.open("Images/best-style-book-personal-libarary.png")
    st.image(image, width=None)
    st.title("Library Manager")
    
    # Navigation dropdown with new option
    page = st.selectbox(
        "Navigation",
        ["Home", "List of Available Books", "Search Book", "Add Book", "Remove Book"]
    )
    
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size: 0.8rem; color: #888;">
        <p>Your Personal Library Manager</p>
        <p>Version 1.0</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Main content area
if page == "Home":
    st.title("📚 Personal Library Manager")


# Open Image
    image = Image.open("Images/Library-Image.png")  # PNG format use karo
    st.image(image, use_container_width=True) 

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="book-card">
            <h3>Your Collection</h3>
            <p>Manage your personal book collection with ease. Add books, search for titles, and keep track of your reading journey.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display summary statistics
        books_df = get_all_books()
        if not books_df.empty:
            total_books = len(books_df)
            total_authors = books_df['author'].nunique()
            genres = books_df['genre'].value_counts()
            
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                st.metric("Total Books", total_books)
            with col_stats2:
                st.metric("Total Authors", total_authors)
            with col_stats3:
                if not genres.empty:
                    st.metric("Most Common Genre", genres.index[0])
                else:
                    st.metric("Most Common Genre", "N/A")
            
            # Display recent additions
            st.markdown("### Recent Additions")
            books_df['date_added'] = pd.to_datetime(books_df['date_added'])
            recent_books = books_df.sort_values('date_added', ascending=False).head(3)
            
            for i, book in recent_books.iterrows():
                st.markdown(f"""
                <div class="book-card">
                    <h4>{book['title']}</h4>
                    <p><strong>By:</strong> {book['author']}</p>
                    <p><strong>Added on:</strong> {book['date_added'].strftime('%B %d, %Y')}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Your library is empty. Start adding books to your collection!")
            
    with col2:
        st.markdown("""
        <div class="book-card">
            <h3>Quick Tips</h3>
            <ul>
                <li>Use the sidebar to navigate between features</li>
                <li>Search for books by title or author</li>
                <li>Add new books to your collection</li>
                <li>Remove books you no longer own</li>
                <li>Download available books to read offline</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="book-card">
            <h3>Features</h3>
            <p>✅ Smart search with AI-powered recommendations</p>
            <p>✅ Beautiful book display</p>
            <p>✅ Easy organization</p>
            <p>✅ Track your collection</p>
            <p>✅ Download available books</p>
        </div>
        """, unsafe_allow_html=True)

elif page == "List of Available Books":
    st.title("Available Books for Download")
    
    books_df = get_all_books()
    
    if books_df.empty:
        st.info("Your library is empty. There are no books available for download.")
    else:
        st.markdown("""
        <div class="book-card">
            <h3>Browse Your Library</h3>
            <p>Here are all the books in your collection that are available for download.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display all books with download buttons
        books_columns = st.columns(3)
        for i, (_, book) in enumerate(books_df.iterrows()):
            with books_columns[i % 3]:
                # Generate download link - handle the case when file_path doesn't exist
                download_link = get_download_link(book.get('file_path', ''), book['title'])
                
                st.markdown(f"""
                <div class="book-card">
                    <h3>{book['title']}</h3>
                    <p><strong>Author:</strong> {book['author']}</p>
                    <p><strong>Genre:</strong> {book['genre']}</p>
                    <p><strong>Year:</strong> {book['published_year']}</p>
                    <p><strong>ISBN:</strong> {book['isbn']}</p>
                    <div style="text-align: center; margin-top: 15px;">
                        <button class="stButton download-btn">{download_link}</button>
                    </div>
                </div>
                """, unsafe_allow_html=True)


elif page == "Search Book":
    st.title("Search Books")
    
    # Search tabs
    search_tab1, search_tab2 = st.tabs(["Search Your Library", "Find New Books"])
    
    with search_tab1:
        local_query = st.text_input("Search your library by title or author")
        if local_query:
            results = search_books(local_query)
            
            if not results.empty:
                st.success(f"Found {len(results)} books in your library")
                
                # Display results in a card layout with download buttons
                cols = st.columns(3)
                for i, (_, book) in enumerate(results.iterrows()):
                    with cols[i % 3]:
                        # Generate download link
                        download_link = get_download_link(book['file_path'], book['title'])
                        
                        st.markdown(f"""
                        <div class="book-card">
                            <h3>{book['title']}</h3>
                            <p><strong>Author:</strong> {book['author']}</p>
                            <p><strong>Genre:</strong> {book['genre']}</p>
                            <p>{book['description'][:100]}...</p>
                            <div style="text-align: center; margin-top: 15px;">
                                <button class="stButton download-btn">{download_link}</button>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No matches found in your library.")
    
    with search_tab2:
        api_query = st.text_input("Search for new books using AI")
        if api_query:
            with st.spinner("Searching for books..."):
                search_results = search_books_api(api_query)
            
            if search_results:
                st.success(f"Found {len(search_results)} books")
                
                # Display results in a card layout with buttons to add and download
                cols = st.columns(3)
                for i, book in enumerate(search_results):
                    with cols[i % 3]:
                        st.markdown(f"""
                        <div class="book-card">
                            <h3>{book['title']}</h3>
                            <p><strong>Author:</strong> {book['author']}</p>
                            <p><strong>Genre:</strong> {book['genre']}</p>
                            <p>{book['description'][:100]}...</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Add buttons for each search result
                        col_btn1, col_btn2 = st.columns(2)
                        
                        with col_btn1:
                            if st.button(f"Add to Library", key=f"add_{i}"):
                                book_data = {
                                    'id': str(uuid.uuid4()),
                                    'title': book['title'],
                                    'author': book['author'],
                                    'genre': book['genre'],
                                    'description': book['description'],
                                    'published_year': book['published_year'],
                                    'isbn': book['isbn'],
                                    'cover_image': book['cover_image'],
                                    'date_added': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    'file_path': f"downloads/{book['title'].replace(' ', '_').lower()}.pdf"
                                }
                                
                                if add_book_to_db(book_data):
                                    st.success(f"Added '{book['title']}' to your library!")
                                else:
                                    st.error("Failed to add book to library.")
                        
                        with col_btn2:
                            # Generate a temporary download link for this search result
                            download_link = get_download_link("", book['title'])
                            st.markdown(f"""
                            <div style="text-align: center;">
                                <button class="stButton download-btn">{download_link}</button>
                            </div>
                            """, unsafe_allow_html=True)

elif page == "Add Book":
    st.title("Add a New Book")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="book-card">
            <h3>Enter Book Details</h3>
            <p>Fill in the information about the book you want to add to your collection.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Book details form
        with st.form("book_form"):
            title = st.text_input("Title*")
            author = st.text_input("Author*")
            genre = st.selectbox("Genre", ["Fiction", "Non-fiction", "Science Fiction", 
                                         "Fantasy", "Mystery", "Thriller", "Romance", 
                                         "Biography", "History", "Science", "Self-Help", 
                                         "Art", "Poetry", "Other"])
            description = st.text_area("Description")
            
            col_form1, col_form2 = st.columns(2)
            with col_form1:
                published_year = st.number_input("Published Year", min_value=0, max_value=datetime.now().year, step=1)
            with col_form2:
                isbn = st.text_input("ISBN")
            
            # Add file upload option
            uploaded_file = st.file_uploader("Upload Book File (PDF, EPUB, etc.)", type=["pdf", "epub", "txt"])
            cover_image = st.text_input("Cover Image URL (optional)")
            
            submit_button = st.form_submit_button("Add to Library")
            
            if submit_button:
                if not title or not author:
                    st.error("Title and author are required fields.")
                else:
                    # Handle file upload if provided
                    file_path = ""
                    if uploaded_file is not None:
                        # Create directory if it doesn't exist
                        if not os.path.exists("uploads"):
                            os.makedirs("uploads")
                        
                        # Save the file
                        file_path = f"uploads/{uploaded_file.name}"
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                    
                    # Create book data dictionary
                    book_data = {
                        'id': str(uuid.uuid4()),
                        'title': title,
                        'author': author,
                        'genre': genre,
                        'description': description,
                        'published_year': published_year,
                        'isbn': isbn,
                        'cover_image': cover_image or f"https://via.placeholder.com/150?text={title.replace(' ', '+')}",
                        'date_added': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'file_path': file_path
                    }
                    
                    if add_book_to_db(book_data):
                        st.success(f"Added '{title}' to your library!")
                        # Clear the form
                        st.experimental_rerun()
                    else:
                        st.error("Failed to add book to library.")
    
    with col2:
        st.markdown("""
        <div class="book-card">
            <h3>Tips for Adding Books</h3>
            <ul>
                <li>Required fields are marked with an asterisk (*)</li>
                <li>Add a cover image URL to make your library more visual</li>
                <li>Upload the book file to make it downloadable</li>
                <li>ISBN is optional but helps with identification</li>
                <li>A good description helps you remember the book later</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="book-card">
            <h3>ISBN Format</h3>
            <p>ISBN-10: 10 digits</p>
            <p>ISBN-13: 13 digits, usually starts with 978 or 979</p>
            <p>Example: 978-3-16-148410-0</p>
        </div>
        """, unsafe_allow_html=True)

elif page == "Remove Book":
    st.title("Remove Books from Your Library")
    
    books_df = get_all_books()
    
    if books_df.empty:
        st.info("Your library is empty. There are no books to remove.")
    else:
        st.markdown("""
        <div class="book-card">
            <h3>Select Books to Remove</h3>
            <p>Choose the books you want to remove from your collection.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display all books with remove buttons
        for i, (_, book) in enumerate(books_df.iterrows()):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                <div class="book-card">
                    <h3>{book['title']}</h3>
                    <p><strong>Author:</strong> {book['author']}</p>
                    <p><strong>Genre:</strong> {book['genre']}</p>
                    <p><strong>Added on:</strong> {book['date_added']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if st.button(f"Remove", key=f"remove_{i}"):
                    if remove_book(book['id']):
                        st.success(f"Removed '{book['title']}' from your library!")
                        # Refresh the page to show updated library
                        st.experimental_rerun()
                    else:
                        st.error("Failed to remove book from library.")

# Add a footer
st.markdown("""
<div style="text-align: center; padding: 20px; color: #888; font-size: 0.8rem;">
    <p>Personal Library Manager | Created By Syed Ali ❤️ using Streamlit</p>
</div>
""", unsafe_allow_html=True)