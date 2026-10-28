from sqlalchemy import text
from backend.database import engine

with engine.connect() as c:
    row=c.execute(text('SELECT DATABASE(), VERSION()')).one()
    print('Connected successfully')
    print('Database:',row[0])
    print('MySQL version:',row[1])
