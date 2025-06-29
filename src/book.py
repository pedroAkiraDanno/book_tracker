import pyodbc
import getpass
from datetime import datetime

class BookTrackingSystem:
    def __init__(self):
        self.connection = None
        self.current_user = None
        
    def connect_to_database(self):
        try:
            self.connection = pyodbc.connect(
                'DRIVER={SQL Server};'
                'SERVER=localhost,1433;'  # Default SQL Server port is 1433 # 'SERVER=localhost\SQLEXPRESS,1433;' #'SERVER=your_server_name\instance_name,port_number;'
                'DATABASE=BookTrackingSystem;'
                'Trusted_Connection=yes;'  # Use Windows Authentication
                # If you need SQL Server authentication instead, use:
                # 'UID=your_username;'
                # 'PWD=your_password;'
            )
            print("Connected to database successfully!")
            return True
        except pyodbc.Error as e:
            print(f"Database connection error: {e}")
            return False
    
    def register_user(self):
        print("\n--- User Registration ---")
        username = input("Enter username: ")
        password = getpass.getpass("Enter password: ")
        email = input("Enter email: ")
        full_name = input("Enter full name: ")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("EXEC sp_RegisterUser ?, ?, ?, ?", 
                         (username, password, email, full_name))
            self.connection.commit()
            print("Registration successful!")
        except pyodbc.Error as e:
            print(f"Registration failed: {e}")
    
    def login(self):
        print("\n--- User Login ---")
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("EXEC sp_AuthenticateUser ?, ?", (username, password))
            row = cursor.fetchone()
            
            if row and row[0]:  # If UserID is not NULL
                self.current_user = {
                    'UserID': row[0],
                    'Username': row[1],
                    'Email': row[2],
                    'FullName': row[3]
                }
                print(f"\nWelcome, {self.current_user['FullName']}!")
                return True
            else:
                print("Invalid username or password.")
                return False
        except pyodbc.Error as e:
            print(f"Login error: {e}")
            return False
    
    def add_book_to_system(self):
        """Add a new book to the global books table"""
        print("\n--- Add New Book to System ---")
        title = input("Title: ").strip()
        author = input("Author: ").strip()
        
        if not title or not author:
            print("Title and author are required!")
            return
            
        isbn = input("ISBN (optional): ").strip() or None
        year = input("Publication year (optional): ").strip() or None
        genre = input("Genre (optional): ").strip() or None
        description = input("Description (optional): ").strip() or None
        pages = input("Page count (optional): ").strip() or None
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO Books (Title, Author, ISBN, PublicationYear, Genre, Description, PageCount)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, author, isbn, year, genre, description, pages))
            
            self.connection.commit()
            print("Book added to system successfully!")
        except pyodbc.Error as e:
            print(f"Error adding book: {e}")
    
    def add_book_to_my_collection(self):
        """Add an existing book to the user's personal collection"""
        if not self.current_user:
            print("Please login first.")
            return
            
        print("\n--- Add Book to My Collection ---")
        search_term = input("Search for book by title or author: ").strip()
        
        if not search_term:
            print("Please enter a search term.")
            return
            
        try:
            cursor = self.connection.cursor()
            
            # Search for books not already in user's collection
            cursor.execute("""
                SELECT b.BookID, b.Title, b.Author 
                FROM Books b
                WHERE (b.Title LIKE ? OR b.Author LIKE ?)
                AND NOT EXISTS (
                    SELECT 1 FROM UserBooks ub 
                    WHERE ub.BookID = b.BookID 
                    AND ub.UserID = ?
                )
            """, (f'%{search_term}%', f'%{search_term}%', self.current_user['UserID']))
            
            books = cursor.fetchall()
            
            if not books:
                print("No matching books found or they're already in your collection.")
                return
                
            print("\nMatching Books:")
            for i, book in enumerate(books, 1):
                print(f"{i}. {book[1]} by {book[2]}")
                
            choice = input("\nEnter the number of the book to add (or 0 to cancel): ")
            
            try:
                choice = int(choice)
                if choice == 0:
                    return
                elif 1 <= choice <= len(books):
                    selected_book = books[choice-1]
                    
                    # Show status options
                    cursor.execute("SELECT StatusID, StatusName FROM BookStatus")
                    statuses = cursor.fetchall()
                    
                    print("\nSelect a status:")
                    for status in statuses:
                        print(f"{status[0]}. {status[1]}")
                    
                    status_id = input("Enter status ID: ")
                    
                    # Add to user's collection
                    cursor.execute("""
                        INSERT INTO UserBooks (UserID, BookID, StatusID)
                        VALUES (?, ?, ?)
                    """, (self.current_user['UserID'], selected_book[0], status_id))
                    
                    self.connection.commit()
                    print(f"Added '{selected_book[1]}' to your collection!")
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Please enter a valid number.")
                
        except pyodbc.Error as e:
            print(f"Error searching books: {e}")
    
    def list_my_books(self):
        if not self.current_user:
            print("Please login first.")
            return
            
        print("\n--- My Book Collection ---")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT b.BookID, b.Title, b.Author, bs.StatusName, 
                       ub.Rating, ub.StartDate, ub.EndDate, ub.Review
                FROM UserBooks ub
                JOIN Books b ON ub.BookID = b.BookID
                JOIN BookStatus bs ON ub.StatusID = bs.StatusID
                WHERE ub.UserID = ?
                ORDER BY b.Title
            """, self.current_user['UserID'])
            
            books = cursor.fetchall()
            
            if not books:
                print("Your collection is empty. Add some books!")
                return
                
            print(f"\n{'ID':<5} {'Title':<30} {'Author':<25} {'Status':<15} {'Rating':<6} {'Dates':<20}")
            print("-" * 100)
            for book in books:
                dates = ""
                if book[5]:
                    dates += f"Start: {book[5].strftime('%Y-%m-%d')}"
                if book[6]:
                    if dates: dates += " "
                    dates += f"End: {book[6].strftime('%Y-%m-%d')}"
                
                print(f"{book[0]:<5} {book[1][:28]:<30} {book[2][:23]:<25} "
                      f"{book[3][:14]:<15} "
                      f"{'★'*book[4]+'☆'*(5-book[4]) if book[4] else 'N/A':<6} "
                      f"{dates:<20}")
                
        except pyodbc.Error as e:
            print(f"Error retrieving books: {e}")
    
    def list_all_books(self):
        """List all books in the system"""
        print("\n--- All Books in System ---")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT BookID, Title, Author, PublicationYear, Genre, Description 
                FROM Books
                ORDER BY Title
            """)
            
            books = cursor.fetchall()
            
            if not books:
                print("No books found in the system.")
                return
                
            print(f"\n{'ID':<5} {'Title':<30} {'Author':<25} {'Year':<6} {'Genre':<15}")
            print("-" * 85)
            for book in books:
                print(f"{book[0]:<5} {book[1][:28]:<30} {book[2][:23]:<25} "
                      f"{str(book[3]) if book[3] else 'N/A':<6} "
                      f"{book[4][:13] if book[4] else 'N/A':<15}")
            
            # Show details if user wants
            book_id = input("\nEnter book ID to see details (or 0 to continue): ")
            if book_id != '0':
                self.show_book_details(book_id)
                
        except pyodbc.Error as e:
            print(f"Error retrieving books: {e}")
    
    def show_book_details(self, book_id):
        """Show detailed information about a specific book"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT BookID, Title, Author, ISBN, PublicationYear, Genre, 
                       Description, PageCount, AddedDate
                FROM Books
                WHERE BookID = ?
            """, book_id)
            
            book = cursor.fetchone()
            
            if not book:
                print("Book not found.")
                return
                
            print("\n--- Book Details ---")
            print(f"ID: {book[0]}")
            print(f"Title: {book[1]}")
            print(f"Author: {book[2]}")
            print(f"ISBN: {book[3] if book[3] else 'N/A'}")
            print(f"Publication Year: {book[4] if book[4] else 'N/A'}")
            print(f"Genre: {book[5] if book[5] else 'N/A'}")
            print(f"Description: {book[6] if book[6] else 'N/A'}")
            print(f"Page Count: {book[7] if book[7] else 'N/A'}")
            print(f"Added to System: {book[8].strftime('%Y-%m-%d')}")
            
            if self.current_user:
                # Check if book is in user's collection
                cursor.execute("""
                    SELECT StatusName 
                    FROM UserBooks ub
                    JOIN BookStatus bs ON ub.StatusID = bs.StatusID
                    WHERE ub.UserID = ? AND ub.BookID = ?
                """, (self.current_user['UserID'], book_id))
                
                status = cursor.fetchone()
                if status:
                    print(f"\nYour Status: {status[0]}")
                else:
                    print("\nThis book is not in your collection yet.")
                    add = input("Would you like to add it to your collection? (y/n): ")
                    if add.lower() == 'y':
                        self.add_book_to_my_collection(book_id)
                        
        except pyodbc.Error as e:
            print(f"Error retrieving book details: {e}")
    
    def search_books_in_system(self):
        """Search books in the global system"""
        print("\n--- Search Books ---")
        search_term = input("Enter title or author to search: ").strip()
        
        if not search_term:
            print("Please enter a search term.")
            return
            
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT b.BookID, b.Title, b.Author, b.PublicationYear, b.Genre
                FROM Books b
                WHERE b.Title LIKE ? OR b.Author LIKE ?
                ORDER BY b.Title
            """, (f'%{search_term}%', f'%{search_term}%'))
            
            books = cursor.fetchall()
            
            if not books:
                print("No books found matching your search.")
                return
                
            print("\nSearch Results:")
            print(f"\n{'ID':<5} {'Title':<30} {'Author':<25} {'Year':<6} {'Genre':<15}")
            print("-" * 85)
            for book in books:
                print(f"{book[0]:<5} {book[1][:28]:<30} {book[2][:23]:<25} "
                      f"{str(book[3]) if book[3] else 'N/A':<6} "
                      f"{book[4][:13] if book[4] else 'N/A':<15}")
            
            # Option to view details
            book_id = input("\nEnter book ID to see details (or 0 to continue): ")
            if book_id != '0':
                self.show_book_details(book_id)
                
        except pyodbc.Error as e:
            print(f"Error searching books: {e}")
    
    def update_book_status(self):
        if not self.current_user:
            print("Please login first.")
            return
            
        self.list_my_books()
        book_id = input("\nEnter the ID of the book to update: ")
        
        try:
            cursor = self.connection.cursor()
            
            # Get current status
            cursor.execute("""
                SELECT ub.UserBookID, bs.StatusName
                FROM UserBooks ub
                JOIN BookStatus bs ON ub.StatusID = bs.StatusID
                WHERE ub.UserID = ? AND ub.BookID = ?
            """, (self.current_user['UserID'], book_id))
            
            current = cursor.fetchone()
            
            if not current:
                print("Book not found in your collection.")
                return
                
            print(f"\nCurrent status: {current[1]}")
            
            # List available statuses
            cursor.execute("SELECT StatusID, StatusName FROM BookStatus")
            statuses = cursor.fetchall()
            
            print("\nAvailable statuses:")
            for status in statuses:
                print(f"{status[0]}. {status[1]}")
                
            new_status = input("Enter new status ID: ")
            
            # Update status
            cursor.execute("""
                UPDATE UserBooks 
                SET StatusID = ?
                WHERE UserBookID = ?
            """, (new_status, current[0]))
            
            # Update dates based on status
            if new_status == '3':  # 'I am reading'
                cursor.execute("""
                    UPDATE UserBooks 
                    SET StartDate = GETDATE()
                    WHERE UserBookID = ? AND StartDate IS NULL
                """, current[0])
            elif new_status == '1':  # 'I read'
                cursor.execute("""
                    UPDATE UserBooks 
                    SET EndDate = GETDATE()
                    WHERE UserBookID = ? AND EndDate IS NULL
                """, current[0])
            
            self.connection.commit()
            print("Book status updated successfully!")
            
        except pyodbc.Error as e:
            print(f"Error updating book status: {e}")
    
    def view_history(self):
        if not self.current_user:
            print("Please login first.")
            return
            
        print("\n--- Your Reading History ---")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT b.Title, old_s.StatusName, new_s.StatusName, h.ChangedDate
                FROM BookHistory h
                JOIN UserBooks ub ON h.UserBookID = ub.UserBookID
                JOIN Books b ON ub.BookID = b.BookID
                LEFT JOIN BookStatus old_s ON h.OldStatusID = old_s.StatusID
                JOIN BookStatus new_s ON h.NewStatusID = new_s.StatusID
                WHERE ub.UserID = ?
                ORDER BY h.ChangedDate DESC
            """, self.current_user['UserID'])
            
            history = cursor.fetchall()
            
            if not history:
                print("No history found.")
                return
                
            print(f"\n{'Book':<30} {'From':<15} {'To':<15} {'Date':<20}")
            print("-" * 80)
            for record in history:
                print(f"{record[0][:28]:<30} {record[1][:14] if record[1] else 'N/A':<15} "
                      f"{record[2][:14]:<15} {record[3].strftime('%Y-%m-%d %H:%M'):<20}")
                
        except pyodbc.Error as e:
            print(f"Error retrieving history: {e}")
    
    def main_menu(self):
        while True:
            print("\n=== Book Tracking System ===")
            if self.current_user:
                print(f"Logged in as: {self.current_user['Username']}")
                print("1. List my books")
                print("2. List all books in system")
                print("3. Add book to system")
                print("4. Add book to my collection")
                print("5. Search books in system")
                print("6. Update book status")
                print("7. View reading history")
                print("8. Logout")
                print("9. Exit")
            else:
                print("1. Login")
                print("2. Register")
                print("3. List all books in system")
                print("4. Exit")
            
            choice = input("Enter your choice: ")
            
            if self.current_user:
                if choice == '1':
                    self.list_my_books()
                elif choice == '2':
                    self.list_all_books()
                elif choice == '3':
                    self.add_book_to_system()
                elif choice == '4':
                    self.add_book_to_my_collection()
                elif choice == '5':
                    self.search_books_in_system()
                elif choice == '6':
                    self.update_book_status()
                elif choice == '7':
                    self.view_history()
                elif choice == '8':
                    self.current_user = None
                    print("Logged out successfully.")
                elif choice == '9':
                    print("Goodbye!")
                    break
                else:
                    print("Invalid choice. Please try again.")
            else:
                if choice == '1':
                    if self.login():
                        continue
                elif choice == '2':
                    self.register_user()
                elif choice == '3':
                    self.list_all_books()
                elif choice == '4':
                    print("Goodbye!")
                    break
                else:
                    print("Invalid choice. Please try again.")

if __name__ == "__main__":
    system = BookTrackingSystem()
    if system.connect_to_database():
        system.main_menu()