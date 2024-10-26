from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func  # Add this import
from typing import Annotated
from models import Users, Forum, Prediction  # Import the Prediction model
from database import SessionLocal
import pandas as pd
from math import ceil
from .auth import get_current_user
import json

router = APIRouter(
    prefix = '',
    tags = ['predict']
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

templates = Jinja2Templates(directory="templates")

def auth_required(request: Request):
    user = get_current_user(request)
    if not user["is_authenticated"]:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

albums = ["Brat", "Chronicles of a Diamond", "Cowboy Carter", "Eternal Sunshine", "Hit Me Hard and Soft", "Short n Sweet", "The Rise and Fall of a Midwest Princess", "The Tortured Poets Department"]
records = ["A Bar Song", "Birds of a Feather", "Die With a Smile", "Espresso", "Good Luck, Babe!", "Not Like Us", "Now and Then", "Texas Hold Em"]
songs = ["Beautiful Things", "Birds of a Feather", "Die With a Smile", "Fortnight", "Good Luck, Babe!", "Not Like Us", "Please Please Please", "Texas Hold Em"]
artists = ["Benson Boone", "Chappell Roan", "Megan Moroney", "Raye", "Sabrina Carpenter", "Shaboozey", "Sierra Ferrell", "Teddy Swims"]

### get ###

@router.get("/")
def return_login_page(request: Request):
    return RedirectResponse(url="/login", status_code=303)

@router.get("/home")
def render_home_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@router.get("/legacy")
def render_legacy_page(request: Request):
    user = get_current_user(request)
    if not user["is_authenticated"]:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("legacy.html", {"request": request, "user": user})

@router.get("/predict")
def render_predict_page(request: Request, db: db_dependency, success: bool = Query(False)):
    user = get_current_user(request)
    if not user["is_authenticated"]:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse("predict.html", {
        "request": request,
        "albums": albums,
        "records": records,
        "songs": songs,
        "artists": artists,
        "user": user
    })

@router.get("/forum")
async def forum(request: Request, db: db_dependency, page: int = Query(1, ge=1)):
    user = get_current_user(request)
    if not user["is_authenticated"]:
        return RedirectResponse(url="/login", status_code=303)
    
    posts_per_page = 10
    total_posts = db.query(Forum).count()
    total_pages = ceil(total_posts / posts_per_page)
    
    offset = (page - 1) * posts_per_page
    posts = db.query(Forum).order_by(Forum.created_at.desc()).offset(offset).limit(posts_per_page).all()
    
    return templates.TemplateResponse("forum.html", {
        "request": request, 
        "posts": posts,
        "current_page": page,
        "total_pages": total_pages,
        "user": user
    })

### post ###

@router.post("/legacy")
async def handle_form(request: Request, artist_name: str = Form(...), year: str = Form(...), category: str = Form(...), song_album_name: str = Form(...), current_user: str = Depends(auth_required)):
    
    user = get_current_user(request)
    if not user["is_authenticated"]:
        return RedirectResponse(url="/login", status_code=303)
    
    df = pd.read_csv("Grammys.csv")

    if artist_name != "":
        df = df[df["Artist"]==artist_name]

    if year != "":
        df = df[df["Year"]==int(year)]

    if category != "":
        df = df[df["Category"]==category]
    
    if song_album_name != "":
        df = df[df["Winner"]==song_album_name]

    if df.empty:
        df_html = ""
    else:
        df_html = df.to_html(classes='dataframe', index=False, escape=False)

    return templates.TemplateResponse("results.html", {"request": request, "df": df_html})

@router.post("/forum")
async def post_message(request: Request, db: db_dependency, message: str = Form(...)):
    user = get_current_user(request)
    if not user["is_authenticated"]:
        return RedirectResponse(url="/login", status_code=303)
    
    new_post = Forum(post_body=message, username=user["username"])
    db.add(new_post)
    db.commit()
    return RedirectResponse(url="/forum", status_code=303)

@router.post("/predict")
async def submit_prediction(
    request: Request,
    db: db_dependency,
    album_of_the_year: str = Form(...),
    record_of_the_year: str = Form(...),
    song_of_the_year: str = Form(...),
    best_new_artist: str = Form(...)
):
    user = get_current_user(request)
    if not user["is_authenticated"]:
        return RedirectResponse(url="/login", status_code=303)
    
    # Check if the user already has a prediction
    existing_prediction = db.query(Prediction).filter(Prediction.username == user["username"]).first()
    
    if existing_prediction:
        # Update existing prediction
        existing_prediction.album = album_of_the_year
        existing_prediction.record = record_of_the_year
        existing_prediction.song = song_of_the_year
        existing_prediction.artist = best_new_artist
    else:
        # Create new prediction
        new_prediction = Prediction(
            username=user["username"],
            album=album_of_the_year,
            record=record_of_the_year,
            song=song_of_the_year,
            artist=best_new_artist
        )
        db.add(new_prediction)
    
    db.commit()
    
    # Fetch current predictions data
    album_data = db.query(Prediction.album, func.count(Prediction.album)).group_by(Prediction.album).all()
    record_data = db.query(Prediction.record, func.count(Prediction.record)).group_by(Prediction.record).all()
    song_data = db.query(Prediction.song, func.count(Prediction.song)).group_by(Prediction.song).all()
    artist_data = db.query(Prediction.artist, func.count(Prediction.artist)).group_by(Prediction.artist).all()

    # Prepare data for charts
    def prepare_chart_data(data, all_nominees):
        data_dict = dict(data)
        labels = all_nominees
        counts = [data_dict.get(nominee, 0) for nominee in all_nominees]
        return json.dumps({"labels": labels, "data": counts})

    return templates.TemplateResponse("currentbets.html", {
        "request": request,
        "user": user,
        "album_data": prepare_chart_data(album_data, albums),
        "record_data": prepare_chart_data(record_data, records),
        "song_data": prepare_chart_data(song_data, songs),
        "artist_data": prepare_chart_data(artist_data, artists)
    })
