from src.data_fusion_agent import SuperEfficientDataFusionAgent, FirebaseClient
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import logging
import json
import os
from datetime import datetime
import google.generativeai as genai
from firebase_admin import firestore
import traceback
import re
import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Add project root to the Python path
# This is a more robust way to handle imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)


# Initialize FastAPI app
app = FastAPI(
    title="Bengaluru City Intelligence API",
    description="AI-powered city data analysis and social media monitoring",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firebase and Gemini (with error handling)
try:
    firebase_client = FirebaseClient()
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    vision_model = genai.GenerativeModel('gemini-1.5-flash')
    city_agent = SuperEfficientDataFusionAgent()
except Exception as e:
    logger.error(f"FATAL: Could not initialize core services: {e}")
    traceback.print_exc()
    # In a real app, you might exit or have a degraded mode.
    # For now, we'll let it continue to show the error on API calls.
    firebase_client = None
    vision_model = None
    city_agent = None


# Thread pool for CPU-bound operations
executor = ThreadPoolExecutor(max_workers=4)

# City data categories for image analysis
CITY_CATEGORIES = [
    "traffic_congestion",
    "road_infrastructure",
    "public_transport",
    "urban_construction",
    "civic_facilities",
    "environmental_issues",
    "public_safety",
    "community_events",
    "utility_services",
    "urban_planning"
]

# Pydantic Models


class Coordinates(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    estimated_area: Optional[str] = None


class AgentInference(BaseModel):
    summary: str
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    actionable_insights: str
    traffic_impact: str = Field(..., pattern="^(yes|no|unknown)$")
    time_sensitivity: str = Field(...,
                                  pattern="^(immediate|hours|days|ongoing)$")
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class ImageAnalysisResponse(BaseModel):
    coordinates: Coordinates
    category: str
    agentInference: AgentInference
    detected_elements: List[str]
    recommendations: List[str]
    metadata: Optional[Dict[str, Any]] = None


class EventPreferences(BaseModel):
    categories: List[str] = ['traffic',
                             'infrastructure', 'weather', 'events', 'civic']
    keywords: List[str] = ['bengaluru',
                           'bangalore', 'traffic', 'metro', 'rain']
    min_urgency: int = Field(default=3, ge=1, le=10)
    relevant_areas: List[str] = ['all']


class SocialFetchRequest(BaseModel):
    preferences: Optional[EventPreferences] = None


class EventCoordinates(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area: str = "Bengaluru"


class EventAgentInference(BaseModel):
    severity: str
    urgency_score: int
    actionable_advice: str
    affects_traffic: bool
    estimated_duration: Optional[str] = None
    processed_by: str
    timestamp: Optional[str] = None
    source_subreddit: Optional[str] = None
    original_title: str


class EventResponse(BaseModel):
    event: str
    coordinates: EventCoordinates
    category: str
    agentInference: EventAgentInference


class FetchEventsResponse(BaseModel):
    status: str
    total_events: int
    events: List[EventResponse]
    filters_applied: Dict[str, Any]
    fetched_at: str


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    available_endpoints: List[str]

# Async helper functions


async def analyze_image_with_gemini(image_data: bytes, prompt: str) -> str:
    """Async wrapper for Gemini vision analysis"""
    if not vision_model:
        raise HTTPException(
            status_code=503, detail="Vision model not initialized")
    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(
            executor,
            lambda: vision_model.generate_content([prompt, image_data])
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini analysis error: {e}")
        raise HTTPException(
            status_code=500, detail=f"AI analysis failed: {str(e)}")


async def store_analysis_result(analysis_result: dict) -> str:
    """Async wrapper for Firestore storage"""
    if not firebase_client:
        raise HTTPException(
            status_code=503, detail="Firebase client not initialized")
    loop = asyncio.get_event_loop()
    try:
        doc_ref = await loop.run_in_executor(
            executor,
            lambda: firebase_client.db.collection('image_analysis').add({
                **analysis_result,
                'image_processed_at': datetime.now(),
                'status': 'analyzed'
            })
        )
        return doc_ref[1].id
    except Exception as e:
        logger.error(f"Firestore storage error: {e}")
        raise HTTPException(status_code=500, detail="Failed to store analysis")

# API Endpoints


@app.post("/api/upload-image", response_model=ImageAnalysisResponse)
async def upload_and_analyze_image(
    image: UploadFile = File(..., description="Image file to analyze"),
    location: str = Form(default="Bengaluru", description="Location hint"),
    description: str = Form(
        default="", description="User description of the image")
):
    """
    Upload and analyze images using Gemini Vision AI
    Returns coordinates, inferences, and city data category
    """
    try:
        if not image.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400, detail="File must be an image")

        image_data = await image.read()

        if len(image_data) == 0:
            raise HTTPException(status_code=400, detail="Empty image file")

        prompt = f"""
        BENGALURU CITY DATA ANALYZER - IMAGE ANALYSIS
        
        Analyze this image in the context of city data intelligence for Bengaluru/Bangalore.
        Location hint: {location}
        User description: {description}
        
        Provide a detailed JSON response with the following structure:
        {{
            "coordinates": {{
                "latitude": null,
                "longitude": null,
                "estimated_area": "area_name_if_recognizable"
            }},
            "category": "select_from_categories_below",
            "agentInference": {{
                "summary": "brief_description_of_what_you_see",
                "severity": "low/medium/high/critical",
                "actionable_insights": "what_citizens_should_know",
                "traffic_impact": "yes/no/unknown",
                "time_sensitivity": "immediate/hours/days/ongoing",
                "confidence_score": 0.0-1.0
            }},
            "detected_elements": [
                "list_of_key_elements_detected"
            ],
            "recommendations": [
                "actionable_recommendations_for_authorities_or_citizens"
            ]
        }}
        
        Categories to choose from:
        {', '.join(CITY_CATEGORIES)}
        
        Focus on:
        - Urban infrastructure issues
        - Traffic and transportation
        - Public safety concerns
        - Environmental problems
        - Construction and development
        - Community activities
        
        If coordinates cannot be determined from the image, set them to null.
        Be specific about location if landmarks are visible.
        """

        response_text = await analyze_image_with_gemini(image_data, prompt)

        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            raise HTTPException(
                status_code=500, detail="Failed to parse AI response")

        analysis_result = json.loads(json_match.group())

        analysis_result['metadata'] = {
            'timestamp': datetime.now().isoformat(),
            'location_hint': location,
            'user_description': description,
            'file_size': len(image_data),
            'filename': image.filename,
            'content_type': image.content_type,
            'processed_by': 'gemini-vision'
        }

        doc_id = await store_analysis_result(analysis_result)
        analysis_result['metadata']['document_id'] = doc_id

        logger.info(f"Image analyzed and stored with ID: {doc_id}")

        return ImageAnalysisResponse(**analysis_result)

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to parse AI response")
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/trigger-social-fetch")
async def trigger_social_media_fetch(request: SocialFetchRequest = None):
    """
    Trigger social media fetching and processing
    """
    if not city_agent:
        raise HTTPException(
            status_code=503, detail="City agent not initialized")
    try:
        if request is None or request.preferences is None:
            preferences = EventPreferences().dict()
        else:
            preferences = request.preferences.dict()

        logger.info(
            f"Triggering social media fetch with preferences: {preferences}")

        loop = asyncio.get_event_loop()
        inputs = {'preferences': preferences}
        result = await loop.run_in_executor(
            executor,
            lambda: city_agent.run(inputs)
        )

        response_data = {
            'status': 'success',
            'message': 'Social media fetch completed',
            'processing_summary': result,
            'triggered_at': datetime.now().isoformat(),
            'preferences_used': preferences
        }

        logger.info(f"Social media fetch completed: {result}")

        return JSONResponse(content=response_data, status_code=200)

    except Exception as e:
        logger.error(f"Social media fetch error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'message': f'Fetch failed: {str(e)}',
                'triggered_at': datetime.now().isoformat()
            }
        )


@app.get("/api/fetch-events", response_model=FetchEventsResponse)
async def fetch_stored_events(
    limit: int = Query(default=100, ge=1, le=1000,
                       description="Maximum number of events to fetch"),
    category: Optional[str] = Query(
        default=None, description="Filter by category"),
    severity: Optional[str] = Query(
        default=None, pattern="^(low|medium|high|critical)$", description="Filter by severity"),
    hours_back: int = Query(default=24, ge=1, le=168,
                            description="Hours back to fetch events")
):
    """
    Retrieve stored events from Firestore with filtering options
    """
    if not firebase_client:
        raise HTTPException(
            status_code=503, detail="Firebase client not initialized")
    try:
        time_threshold = datetime.now().timestamp() - (hours_back * 3600)

        loop = asyncio.get_event_loop()

        def query_firestore():
            query = firebase_client.db.collection('live_events')

            if category:
                query = query.where('category', '==', category)
            if severity:
                query = query.where('severity', '==', severity)

            query = query.order_by(
                'timestamp', direction=firestore.Query.DESCENDING).limit(limit)

            return list(query.stream())

        docs = await loop.run_in_executor(executor, query_firestore)

        events_data = []
        for doc in docs:
            event_data = doc.to_dict()

            if 'created_at' in event_data:
                if hasattr(event_data['created_at'], 'timestamp'):
                    event_time = event_data['created_at'].timestamp()
                else:
                    try:
                        event_time = datetime.fromisoformat(
                            event_data['created_at'].replace('Z', '+00:00')).timestamp()
                    except:
                        event_time = time_threshold + 1

                if event_time < time_threshold:
                    continue

            formatted_event = EventResponse(
                event=event_data.get('summary', ''),
                coordinates=EventCoordinates(
                    latitude=event_data.get('latitude'),
                    longitude=event_data.get('longitude'),
                    area=event_data.get('location', 'Bengaluru')
                ),
                category=event_data.get('category', 'general'),
                agentInference=EventAgentInference(
                    severity=event_data.get('severity', 'medium'),
                    urgency_score=event_data.get('urgency_score', 5),
                    actionable_advice=event_data.get('actionable_advice', ''),
                    affects_traffic=event_data.get('affects_traffic', False),
                    estimated_duration=event_data.get('estimated_duration'),
                    processed_by=event_data.get('processed_by', 'unknown'),
                    timestamp=event_data.get('timestamp'),
                    source_subreddit=event_data.get('source_subreddit'),
                    original_title=event_data.get('original_title', '')
                )
            )

            events_data.append(formatted_event)

        response_data = FetchEventsResponse(
            status='success',
            total_events=len(events_data),
            events=events_data,
            filters_applied={
                'category': category,
                'severity': severity,
                'hours_back': hours_back,
                'limit': limit
            },
            fetched_at=datetime.now().isoformat()
        )

        logger.info(f"Fetched {len(events_data)} events from Firestore")

        return response_data

    except Exception as e:
        logger.error(f"Fetch events error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'message': f'Fetch failed: {str(e)}',
                'fetched_at': datetime.now().isoformat()
            }
        )


@app.get("/api/fetch-image-analysis")
async def fetch_image_analysis(
    limit: int = Query(default=50, ge=1, le=500,
                       description="Maximum number of analyses to fetch"),
    category: Optional[str] = Query(
        default=None, description="Filter by category")
):
    """
    Fetch stored image analysis results
    """
    if not firebase_client:
        raise HTTPException(
            status_code=503, detail="Firebase client not initialized")
    try:
        loop = asyncio.get_event_loop()

        def query_analyses():
            query = firebase_client.db.collection('image_analysis').order_by(
                'image_processed_at', direction=firestore.Query.DESCENDING).limit(limit)

            if category:
                query = query.where('category', '==', category)

            return list(query.stream())

        docs = await loop.run_in_executor(executor, query_analyses)

        analyses = []
        for doc in docs:
            analysis_data = doc.to_dict()

            formatted_analysis = {
                'event': f"Image Analysis: {analysis_data.get('agentInference', {}).get('summary', '')}",
                'coordinates': analysis_data.get('coordinates', {}),
                'category': analysis_data.get('category', 'general'),
                'agentInference': analysis_data.get('agentInference', {}),
                'detected_elements': analysis_data.get('detected_elements', []),
                'recommendations': analysis_data.get('recommendations', []),
                'metadata': analysis_data.get('metadata', {})
            }

            analyses.append(formatted_analysis)

        return JSONResponse(content={
            'status': 'success',
            'total_analyses': len(analyses),
            'analyses': analyses,
            'fetched_at': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Fetch image analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                'status': 'error',
                'message': f'Fetch failed: {str(e)}'
            }
        )


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status='healthy',
        service='Bengaluru City Intelligence API',
        timestamp=datetime.now().isoformat(),
        available_endpoints=[
            '/api/upload-image',
            '/api/trigger-social-fetch',
            '/api/fetch-events',
            '/api/fetch-image-analysis',
            '/docs',
            '/redoc'
        ]
    )

# Startup event


@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI City Intelligence API starting up...")
    logger.info("Available at: http://0.0.0.0:8000")
    logger.info("API Documentation: http://0.0.0.0:8000/docs")

# Shutdown event


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI City Intelligence API shutting down...")
    executor.shutdown(wait=True)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        "backendServer:app",
        host='0.0.0.0',
        port=8000,
        reload=True,
        workers=1
    )
