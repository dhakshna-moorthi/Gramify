from fastapi import APIRouter, Depends, Request, Form, HTTPException, Response
from fastapi.responses import RedirectResponse
from models import Users
from passlib.context import CryptContext
from database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from jose import jwt, JWTError
from datetime import datetime, timedelta

router = APIRouter(
    prefix = '',
    tags = ['auth']
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

bcrypt_context = CryptContext(schemes = ['bcrypt'])

templates = Jinja2Templates(directory="templates")

SECRET_KEY = "your-secret-key"  # Replace with a secure secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return {"username": None, "is_authenticated": False}
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return {"username": None, "is_authenticated": False}
        return {"username": username, "is_authenticated": True}
    except JWTError:
        return {"username": None, "is_authenticated": False}

### get ###

@router.get("/login")
def render_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register")
def render_register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.get("/logout")
async def logout(request: Request, response: Response):
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response

### post ####

@router.post("/login")
async def handle_login(response: Response, db: db_dependency, request: Request, username: str = Form(...), password: str = Form(...)):
    user = db.query(Users).filter(Users.username == username).first()

    if user and bcrypt_context.verify(password, user.hashed_password):
        access_token = create_access_token(data={"sub": user.username})
        response = RedirectResponse(url="/home", status_code=303)
        response.set_cookie(key="access_token", value=access_token, httponly=True)
        return response
    else:
        return templates.TemplateResponse("login.html", {"request": request, "user": get_current_user(request), "error": "Invalid username or password"})

@router.post("/register")
async def handle_register(db: db_dependency, request: Request, username: str = Form(...), name: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    if password == confirm_password:
        user_details = Users(
            username=username,
            name=name,
            hashed_password=bcrypt_context.hash(password),
        )
        db.add(user_details)
        db.commit()
        return RedirectResponse(url="/login", status_code=303)
    else:
        return templates.TemplateResponse("register.html", {"request": request, "user": get_current_user(request), "error": "Passwords do not match"})






