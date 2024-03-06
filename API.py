
import logging
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, Field, validator
import sqlite3
import geopy.distance
import asyncio


# Initialize logging
logging.basicConfig(filename='log.txt',level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Function to create a new SQLite connection and cursor
def get_db():
    db = sqlite3.connect('addresses.db')
    cursor = db.cursor()
    try:
        yield cursor
    finally:
        db.close()

# Create table if it doesn't exist
with sqlite3.connect('addresses.db') as conn:
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS addresses
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     name TEXT NOT NULL, 
                     address TEXT NOT NULL,
                     latitude REAL NOT NULL,
                     longitude REAL NOT NULL)''')

# Address data model with validation
class Address(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: str
    latitude: float
    longitude: float

    @validator('latitude', 'longitude')
    def check_coordinates(cls, v):
        if not (-90 <= v <= 90):
            raise ValueError('Coordinates must be within the range [-90, 90]')
        return v

# API endpoint to create an address
@app.post("/addresses/")
def create_address(address: Address, db: sqlite3.Cursor = Depends(get_db)):
    try:
        db.execute('''INSERT INTO addresses (name, address, latitude, longitude) 
                      VALUES (?, ?, ?, ?)''', 
                      (address.name, address.address, address.latitude, address.longitude))
        db.connection.commit()
        logger.info(f"Address created: {address}")
        return {"message": "Address created successfully"}
    except Exception as e:
        logger.error(f"Error creating address: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API endpoint to update an address
@app.put("/addresses/{address_id}")
def update_address(address_id: int, address: Address, db: sqlite3.Cursor = Depends(get_db)):
    try:
        db.execute('''UPDATE addresses SET name=?, address=?, latitude=?, longitude=?
                      WHERE id=?''', 
                      (address.name, address.address, address.latitude, address.longitude, address_id))
        db.connection.commit()
        logger.info(f"Address updated: {address}")
        return {"message": "Address updated successfully"}
    except Exception as e:
        logger.error(f"Error updating address: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API endpoint to delete an address
@app.delete("/addresses/{address_id}")
def delete_address(address_id: int, db: sqlite3.Cursor = Depends(get_db)):
    try:
        db.execute("DELETE FROM addresses WHERE id=?", (address_id,))
        db.connection.commit()
        logger.info(f"Address deleted: ID - {address_id}")
        return {"message": "Address deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting address: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API endpoint to retrieve addresses within a given distance and coordinates
@app.get("/addresses/nearby/")
def get_addresses_nearby(latitude: float = Query(..., title="Latitude", ge=-90, le=90),
                         longitude: float = Query(..., title="Longitude", ge=-180, le=180),
                         distance: float = Query(..., title="Distance (in km)", gt=0),
                         db: sqlite3.Cursor = Depends(get_db)):
    try:
        db.execute("SELECT * FROM addresses")
        all_addresses = db.fetchall()
        nearby_addresses = []
        user_location = (latitude, longitude)
        
        for addr in all_addresses:
            addr_location = (addr[3], addr[4])
            if geopy.distance.geodesic(user_location, addr_location).km <= distance:
                nearby_addresses.append({
                    "id": addr[0],
                    "name": addr[1],
                    "address": addr[2],
                    "latitude": addr[3],
                    "longitude": addr[4]
                })
        
        logger.info(f"Addresses retrieved nearby: {nearby_addresses}")
        return nearby_addresses
    except Exception as e:
        logger.error(f"Error retrieving nearby addresses: {e}")
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.main())