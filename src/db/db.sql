















-- Create database
CREATE DATABASE BookTrackingSystem;
GO

USE BookTrackingSystem;
GO

-- Create Users table with password encryption
CREATE TABLE Users (
    UserID INT IDENTITY(1,1) PRIMARY KEY,
    Username NVARCHAR(50) NOT NULL UNIQUE,
    Password VARBINARY(256) NOT NULL, -- Store hashed password
    Email NVARCHAR(100) NOT NULL UNIQUE,
    FullName NVARCHAR(100),
    CreatedDate DATETIME DEFAULT GETDATE(),
    LastLogin DATETIME
);
GO

-- Create Status table
CREATE TABLE BookStatus (
    StatusID INT IDENTITY(1,1) PRIMARY KEY,
    StatusName NVARCHAR(50) NOT NULL UNIQUE,
    Description NVARCHAR(255)
);
GO

-- Insert default statuses
INSERT INTO BookStatus (StatusName, Description)
VALUES 
    ('I read', 'Books already read'),
    ('I want to read', 'Books I plan to read in the future'),
    ('I am reading', 'Books currently being read');
GO

-- Create Books table
CREATE TABLE Books (
    BookID INT IDENTITY(1,1) PRIMARY KEY,
    Title NVARCHAR(255) NOT NULL,
    Author NVARCHAR(255) NOT NULL,
    ISBN NVARCHAR(20),
    PublicationYear INT,
    Genre NVARCHAR(100),
    Description NVARCHAR(MAX),
    PageCount INT,
    AddedDate DATETIME DEFAULT GETDATE()
);
GO

-- Create UserBooks table (junction table for many-to-many relationship)
CREATE TABLE UserBooks (
    UserBookID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT NOT NULL,
    BookID INT NOT NULL,
    StatusID INT NOT NULL,
    Rating INT CHECK (Rating BETWEEN 1 AND 5),
    Review NVARCHAR(MAX),
    StartDate DATETIME,
    EndDate DATETIME,
    FOREIGN KEY (UserID) REFERENCES Users(UserID),
    FOREIGN KEY (BookID) REFERENCES Books(BookID),
    FOREIGN KEY (StatusID) REFERENCES BookStatus(StatusID),
    CONSTRAINT UC_UserBook UNIQUE (UserID, BookID)
);
GO

-- Create History table for tracking changes
CREATE TABLE BookHistory (
    HistoryID INT IDENTITY(1,1) PRIMARY KEY,
    UserBookID INT NOT NULL,
    ChangedDate DATETIME DEFAULT GETDATE(),
    OldStatusID INT,
    NewStatusID INT NOT NULL,
    Notes NVARCHAR(255),
    FOREIGN KEY (UserBookID) REFERENCES UserBooks(UserBookID),
    FOREIGN KEY (OldStatusID) REFERENCES BookStatus(StatusID),
    FOREIGN KEY (NewStatusID) REFERENCES BookStatus(StatusID)
);
GO

-- Create trigger to track status changes
CREATE TRIGGER trg_UserBooks_StatusChange
ON UserBooks
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Only log if status changed
    IF UPDATE(StatusID)
    BEGIN
        INSERT INTO BookHistory (UserBookID, OldStatusID, NewStatusID, Notes)
        SELECT 
            i.UserBookID,
            d.StatusID,
            i.StatusID,
            'Status changed by user'
        FROM inserted i
        INNER JOIN deleted d ON i.UserBookID = d.UserBookID
        WHERE i.StatusID <> d.StatusID;
    END
END;
GO

-- Create stored procedure for user registration
CREATE PROCEDURE sp_RegisterUser
    @Username NVARCHAR(50),
    @Password NVARCHAR(100),
    @Email NVARCHAR(100),
    @FullName NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Check if username or email already exists
    IF EXISTS (SELECT 1 FROM Users WHERE Username = @Username OR Email = @Email)
    BEGIN
        RAISERROR('Username or email already exists', 16, 1);
        RETURN;
    END
    
    -- Hash the password
    DECLARE @HashedPassword VARBINARY(256) = HASHBYTES('SHA2_256', CONVERT(VARCHAR(100), @Password));
    
    -- Insert new user
    INSERT INTO Users (Username, Password, Email, FullName)
    VALUES (@Username, @HashedPassword, @Email, @FullName);
    
    SELECT 'User registered successfully' AS Message;
END;
GO

-- Create stored procedure for user login
CREATE PROCEDURE sp_AuthenticateUser
    @Username NVARCHAR(50),
    @Password NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @HashedPassword VARBINARY(256) = HASHBYTES('SHA2_256', CONVERT(VARCHAR(100), @Password));
    
    IF EXISTS (
        SELECT 1 FROM Users 
        WHERE Username = @Username 
        AND Password = @HashedPassword
    )
    BEGIN
        -- Update last login time
        UPDATE Users SET LastLogin = GETDATE() WHERE Username = @Username;
        SELECT UserID, Username, Email, FullName FROM Users WHERE Username = @Username;
    END
    ELSE
    BEGIN
        SELECT NULL AS UserID, NULL AS Username, NULL AS Email, NULL AS FullName;
    END
END;
GO












-- pip install pyodbc




