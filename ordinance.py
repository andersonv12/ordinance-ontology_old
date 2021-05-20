import sqlite3

class Ordinance:
    def __init__(self, url, content=''):
        self.id = 0
        self.url = url
        self.content = content

class OrdinanceDAO:
    @staticmethod
    def insert(ordinance):
        connection = sqlite3.connect('db/database.db')
        cursor = connection.cursor()
        if not OrdinanceDAO.exists(ordinance):
            statement = 'INSERT INTO ordinances (url, content) VALUES (?, ?)'
            cursor.execute(statement, (ordinance.url, ordinance.content))
            connection.commit()
            print(' - Saved on database!')
        else:
            print(' - It is already saved on database!')

    @staticmethod
    def get(id):
        connection = sqlite3.connect('db/database.db')
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        statement = 'SELECT * FROM ordinances WHERE id = ?'
        cursor.execute(statement, (id,))
        return cursor.fetchall()

    @staticmethod
    def get_all():
        connection = sqlite3.connect('db/database.db')
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        statement = 'SELECT * FROM ordinances'
        cursor.execute(statement)
        return cursor.fetchall()

    @staticmethod
    def exists(ordinance):
        connection = sqlite3.connect('db/database.db')
        cursor = connection.cursor()
        statement = 'SELECT * FROM ordinances WHERE url = ?'
        cursor.execute(statement, (ordinance.url,))
        result = cursor.fetchall()
        if result:
            return True
        return False
