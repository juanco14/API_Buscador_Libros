from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import requests

app = FastAPI(
    title="API BUSCADOR DE LIBROS",
    version="1.0.0",
    description="API para buscar libros usando OPEN LIBRARY API"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

GOOGLE_BOOKS_BASE_URL = "https://www.googleapis.com/books/v1"

OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
OPENLIBRARY_WORKS_URL = "https://openlibrary.org/works"


def simplify_openlibrary_book(item: dict) -> dict:
    work_key = item.get("key", "")  # ejemplo: /works/OL82563W
    work_id = work_key.split("/")[-1] if work_key else None

    cover_id = item.get("cover_i")
    thumbnail = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None

    return {
        "id": work_id,
        "title": item.get("title"),
        "authors": item.get("author_name", []),
        "published_date": item.get("first_publish_year"),
        "publisher": item.get("publisher", [None])[0] if item.get("publisher") else None,
        "thumbnail": thumbnail,
        "categories": item.get("subject", [])[:5] if item.get("subject") else [],
        "description": None
    }

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "books": [],
            "query": ""
        }
    )


@app.get("/search")
def search_books(
    q: str = Query(..., min_length=2, description="Texto de búsqueda del libro"),
    max_results: int = Query(10, ge=1, le=20)
):
    params = {
        "q": q,
        "limit": max_results
    }

    response = requests.get(OPENLIBRARY_SEARCH_URL, params=params, timeout=20)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error consultando OpenLibrary")

    data = response.json()
    docs = data.get("docs", [])
    books = [simplify_openlibrary_book(item) for item in docs]

    return {
        "query": q,
        "total_items": data.get("numFound", 0),
        "results_returned": len(books),
        "books": books
    }
    
@app.get("/books/{book_id}")
def get_book_detail(book_id: str):
    url = f"{OPENLIBRARY_WORKS_URL}/{book_id}.json"
    response = requests.get(url, timeout=20)

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Libro no encontrado")

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error consultando OpenLibrary")

    item = response.json()

    description = item.get("description")
    if isinstance(description, dict):
        description = description.get("value")

    return {
        "id": book_id,
        "title": item.get("title"),
        "description": description,
        "subjects": item.get("subjects", [])[:10]
    }

@app.get("/web/search", response_class=HTMLResponse)
def search_books_web(
    request: Request,
    q: str = Query("", min_length=0),
    max_results: int = Query(10, ge=1, le=20)
):
    books = []

    if q.strip():
        params = {
            "q": q,
            "limit": max_results
        }

        response = requests.get(OPENLIBRARY_SEARCH_URL, params=params, timeout=20)

        if response.status_code == 200:
            data = response.json()
            docs = data.get("docs", [])
            books = [simplify_openlibrary_book(item) for item in docs]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "books": books,
            "query": q
        }
    )

@app.get("/web/books/{book_id}", response_class=HTMLResponse)
def book_detail_web(request: Request, book_id: str):
    url = f"{OPENLIBRARY_WORKS_URL}/{book_id}.json"
    response = requests.get(url, timeout=20)

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Libro no encontrado")

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error consultando OpenLibrary")

    item = response.json()

    description = item.get("description")
    if isinstance(description, dict):
        description = description.get("value")

    book = {
        "id": book_id,
        "title": item.get("title"),
        "description": description,
        "subjects": item.get("subjects", [])[:10],
        "authors": [],
        "publisher": None,
        "published_date": None,
        "thumbnail": None,
        "categories": item.get("subjects", [])[:10]
    }

    return templates.TemplateResponse(
        "detail.html",
        {
            "request": request,
            "book": book
        }
    )