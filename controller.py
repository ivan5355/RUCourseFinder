import json
import os
import numpy as np
import asyncio
import aiohttp
import pandas as pd
import openai
from pinecone import Pinecone
import re
import dotenv



class course_search:
    def __init__(self):
        load_dotenv()

        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.mapbox_access_token = os.getenv("MAPBOX_ACCESS_TOKEN")

         # Initialize OpenAI and Pinecone clients
        openai.api_key = self.openai_api_key
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        self.index = self.pc.Index("courses")

         # Load courses data
        with open(courses_data_path, 'r') as json_file:
            self.courses_data = json.load(json_file)

