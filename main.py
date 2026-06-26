from fastapi import FastAPI
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

def db_query(query_string: str):
      conn = psycopg2.connect(
          host=os.getenv("DB_HOST"),
          port=os.getenv("DB_PORT", "5432"),
          dbname=os.getenv("DB_NAME"),
          user=os.getenv("DB_USER"),
          password=os.getenv("DB_PASSWORD"),
          sslmode="require",
      )
      cur = conn.cursor()
      cur.execute(query_string)
      results = cur.fetchall()
      cur.close()
      conn.close()
      return results



@app.get("/")
def read_root():
    return {"Hello": os.getenv("APP_MESSAGE", "Default Message")}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

