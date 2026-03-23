# code for utility functions 
    # hasing of pw
    # verification of pw
# so that imports and code is not repeated in multiple files/main file 

from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypassword")

def get_password_hash(password):
    return password_hash.hash(password)

def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)

def CPIcalc():
    pass



