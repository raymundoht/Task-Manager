import os
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.environ.get("PORT", 3000))
MONGODB_URI = os.environ.get(
    "MONGODB_URI",
    "mongodb+srv://rayherrera313:rNywYUHJVMjrIQnP@cluster0.gc3uhfs.mongodb.net/proyectoclase?appName=Cluster0"
)
DATABASE_NAME = "task_manager"
