import mysql.connector as mysql


db = mysql.connect(
    host = "localhost",
    user = "admin",
    passwd = "password",
    database = "class_assignments"
)

cursor = db.cursor()
# cursor.execute("CREATE DATABASE class_assignments")
# cursor.execute("CREATE TABLE users (id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), user_name VARCHAR(255))")
cursor.execute("SHOW TABLES")
tables = cursor.fetchall() ## it returns list of tables present in the database
try:
    cursor.execute("DESC users")
    print cursor.fetchall()
except:
    cursor.execute(
        "CREATE TABLE users (id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), user_name VARCHAR(255))")
    cursor.execute("DESC users")
    print cursor.fetchall()

## it will print all the columns as 'tuples' in a list

## showing all the tables one by one
for table in tables:
    print table

query = "INSERT INTO users (name, user_name) VALUES (%s, %s)"
## storing values in a variable
values = ("Hafeez", "hafeez")

## executing the query with values
cursor.execute(query, values)

## to make final output we have to run the 'commit()' method of the database object
db.commit()

print cursor.rowcount, "record inserted"

query = "INSERT INTO users (name, user_name) VALUES (%s, %s)"
## storing values in a variable
values = [
    ("Peter", "peter"),
    ("Amy", "amy"),
    ("Michael", "michael"),
    ("Hennah", "hennah")
]

## executing the query with values
cursor.executemany(query, values)

## to make final output we have to run the 'commit()' method of the database object
db.commit()

print cursor.rowcount, "records inserted"