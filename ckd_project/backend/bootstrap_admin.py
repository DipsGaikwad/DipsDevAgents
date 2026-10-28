"""Create the first Admin safely from terminal. Run only after .env and users migration exist."""
import getpass
from sqlalchemy import select
from backend.database import SessionLocal
from backend.models import User
from backend.auth import hash_password

def main():
    print('CKD Care first Admin setup')
    username=input('Admin username: ').strip()
    full_name=input('Admin full name: ').strip()
    email=input('Admin email: ').strip()
    password=getpass.getpass('Admin password (10+ characters): ')
    if len(password)<10: raise SystemExit('Use at least 10 characters.')
    db=SessionLocal()
    try:
        existing=db.scalar(select(User).where((User.username==username)|(User.email==email)))
        if existing:
            print('This username/email already exists. This script will not change an existing account.')
            raise SystemExit(2)
        user=User(username=username,full_name=full_name,email=email,password_hash=hash_password(password),role='ADMIN',account_status='APPROVED')
        db.add(user); db.commit()
        print(f'Admin created. user_id={user.user_id}. Sign in using that username/password.')
    finally: db.close()
if __name__=='__main__': main()
