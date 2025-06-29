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
                'SERVER=localhost;'
                'DATABASE=BookTrackingSystem;'
                'UID=sa;'
                'PWD=p0w2i8'
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
    
    def add_book(self):
        if not self.current_user:
            print("Please login first.")
            return
            
        print("\n--- Add New Book ---")
        title = input("Title: ")
        author = input("Author: ")
        isbn = input("ISBN (optional): ")
        year = input("Publication year (optional): ")
        genre = input("Genre (optional): ")
        description = input("Description (optional): ")
        pages = input("Page count (optional): ")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO Books (Title, Author, ISBN, PublicationYear, Genre, Description, PageCount)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                SELECT SCOPE_IDENTITY() AS BookID;
            """, (title, author, isbn, year if year else None, genre, description, pages if pages else None))
            
            book_id = cursor.fetchone()[0]
            
            # Add to user's collection with default status
            cursor.execute("""
                INSERT INTO UserBooks (UserID, BookID, StatusID)
                VALUES (?, ?, (SELECT StatusID FROM BookStatus WHERE StatusName = 'I want to read'))
            """, (self.current_user['UserID'], book_id))
            
            self.connection.commit()
            print("Book added successfully!")
        except pyodbc.Error as e:
            print(f"Error adding book: {e}")
    
    def list_books(self):
        if not self.current_user:
            print("Please login first.")
            return
            
        print("\n--- Your Book Collection ---")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT b.BookID, b.Title, b.Author, bs.StatusName, ub.Rating, ub.StartDate, ub.EndDate
                FROM UserBooks ub
                JOIN Books b ON ub.BookID = b.BookID
                JOIN BookStatus bs ON ub.StatusID = bs.StatusID
                WHERE ub.UserID = ?
                ORDER BY b.Title
            """, self.current_user['UserID'])
            
            books = cursor.fetchall()
            
            if not books:
                print("You don't have any books in your collection yet.")
                return
                
            for book in books:
                print(f"\nID: {book[0]}")
                print(f"Title: {book[1]}")
                print(f"Author: {book[2]}")
                print(f"Status: {book[3]}")
                if book[4]:
                    print(f"Rating: {'★' * book[4]}{'☆' * (5 - book[4])}")
                if book[5]:
                    print(f"Started: {book[5].strftime('%Y-%m-%d')}")
                if book[6]:
                    print(f"Finished: {book[6].strftime('%Y-%m-%d')}")
                
        except pyodbc.Error as e:
            print(f"Error retrieving books: {e}")
    
    def update_book_status(self):
        if not self.current_user:
            print("Please login first.")
            return
            
        self.list_books()
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
                
            for record in history:
                print(f"\nBook: {record[0]}")
                print(f"From: {record[1] if record[1] else 'N/A'}")
                print(f"To: {record[2]}")
                print(f"Date: {record[3].strftime('%Y-%m-%d %H:%M')}")
                
        except pyodbc.Error as e:
            print(f"Error retrieving history: {e}")
    
    def main_menu(self):
        while True:
            print("\n=== Book Tracking System ===")
            if self.current_user:
                print(f"Logged in as: {self.current_user['Username']}")
                print("1. List my books")
                print("2. Add a new book")
                print("3. Update book status")
                print("4. View reading history")
                print("5. Logout")
                print("6. Exit")
            else:
                print("1. Login")
                print("2. Register")
                print("3. Exit")
            
            choice = input("Enter your choice: ")
            
            if self.current_user:
                if choice == '1':
                    self.list_books()
                elif choice == '2':
                    self.add_book()
                elif choice == '3':
                    self.update_book_status()
                elif choice == '4':
                    self.view_history()
                elif choice == '5':
                    self.current_user = None
                    print("Logged out successfully.")
                elif choice == '6':
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
                    print("Goodbye!")
                    break
                else:
                    print("Invalid choice. Please try again.")

if __name__ == "__main__":
    system = BookTrackingSystem()
    if system.connect_to_database():
        system.main_menu()