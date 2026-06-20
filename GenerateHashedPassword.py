from werkzeug.security import generate_password_hash
import pyodbc

conn = pyodbc.connect(
    r"Driver={ODBC Driver 17 for SQL Server};"
    r"Server=DESKTOP-8MI2AQC\SQLEXPRESS;"
    r"Database=Salamtak;"
    r"Trusted_Connection=yes;"
)

cursor = conn.cursor()

# new password
hashed_password = generate_password_hash("123")

# update admin user (id = 1002)
cursor.execute("""
    UPDATE users
    SET password = ?
    WHERE id = ?
""", (hashed_password, 1002))

conn.commit()
conn.close()

print("Admin password updated successfully")