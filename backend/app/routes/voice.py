"""
Voice Agent Routes - FastAPI endpoints for voice interactions
"""
import logging
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.security import get_current_user
from app.models import User
from app.services.voice_service import get_voice_service
from app.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])


# Request/Response Models
class VoiceAnswerRequest(BaseModel):
    text: str


class VoiceAnswerResponse(BaseModel):
    answer_text: str
    flags: list[str] = []
    used_context: dict = {}


class VoiceTTSRequest(BaseModel):
    text: str


class VoiceContextResponse(BaseModel):
    profile_complete: bool
    has_personalization: bool = False
    summary: dict


class TTSStatusResponse(BaseModel):
    configured: bool
    missing: list[str] = []
    env_seen: dict
    voice_id: str | None = None


def get_elevenlabs_config_runtime():
    """
    Get ElevenLabs configuration from environment at runtime.
    Checks both settings object and os.environ for maximum compatibility.
    """
    # Check both sources - settings and direct env
    api_key = (
        getattr(settings, "ELEVENLABS_API_KEY", None) or 
        os.getenv("ELEVENLABS_API_KEY") or 
        os.environ.get("ELEVENLABS_API_KEY")
    )
    
    voice_id = (
        getattr(settings, "ELEVENLABS_VOICE_ID", None) or 
        os.getenv("ELEVENLABS_VOICE_ID") or 
        os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    )
    
    # Log what we found for debugging
    logger.info(f"ElevenLabs config check:")
    logger.info(f"  - settings.ELEVENLABS_API_KEY: {bool(getattr(settings, 'ELEVENLABS_API_KEY', None))}")
    logger.info(f"  - os.environ.get('ELEVENLABS_API_KEY'): {bool(os.environ.get('ELEVENLABS_API_KEY'))}")
    logger.info(f"  - Final API key present: {bool(api_key)}")
    logger.info(f"  - Voice ID: {voice_id}")
    
    return api_key, voice_id


@router.get("/tts/status", response_model=TTSStatusResponse)
async def get_tts_status():
    """
    Check if ElevenLabs TTS is properly configured.
    Returns configuration status without exposing sensitive data.
    No authentication required - used for health checks.
    """
    api_key, voice_id = get_elevenlabs_config_runtime()
    
    missing = []
    if not api_key:
        missing.append("ELEVENLABS_API_KEY")
    
    env_seen = {
        "has_key": bool(api_key),
        "has_voice_id": bool(voice_id),
        "settings_has_key": bool(getattr(settings, "ELEVENLABS_API_KEY", None)),
        "environ_has_key": bool(os.environ.get("ELEVENLABS_API_KEY"))
    }
    
    configured = len(missing) == 0
    
    logger.info(f"TTS Status check: configured={configured}, env_seen={env_seen}")
    
    return TTSStatusResponse(
        configured=configured,
        missing=missing,
        env_seen=env_seen,
        voice_id=voice_id if configured else None
    )


@router.get("/context", response_model=VoiceContextResponse)
async def get_voice_context(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user context for voice agent UI.
    Returns profile completeness and personalization status.
    """
    try:
        voice_service = get_voice_service()
        context_data = await voice_service.get_user_context(db, current_user.id)
        
        return VoiceContextResponse(
            profile_complete=context_data.get("profile_complete", True),  # Always allow voice agent
            has_personalization=context_data.get("has_personalization", False),
            summary=context_data.get("summary", {})
        )
    
    except Exception as e:
        logger.error(f"Error getting voice context: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve voice context"
        )


@router.post("/answer", response_model=VoiceAnswerResponse)
async def voice_answer(
    request: VoiceAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a personalized voice response based on user's transcript.
    
    Flow:
    1. Extract user_id from auth token
    2. Fetch user profile and recent reports from DB
    3. Run safety checks (emergency/dosage keywords)
    4. Build personalized prompt with health context
    5. Call LLM to generate answer
    6. Return answer with flags and context info
    """
    try:
        if not request.text or not request.text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text cannot be empty"
            )
        
        voice_service = get_voice_service()
        result = await voice_service.generate_answer(
            db=db,
            user_id=current_user.id,
            text=request.text.strip()
        )
        
        # Check for errors in result
        if "error" in result and not result.get("answer_text"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Unknown error occurred")
            )
        
        return VoiceAnswerResponse(
            answer_text=result.get("answer_text", ""),
            flags=result.get("flags", []),
            used_context=result.get("used_context", {})
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in voice_answer: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {str(e)}"
        )


@router.post("/tts")
async def voice_tts(
    request: VoiceTTSRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Convert text to speech using ElevenLabs TTS API.
    
    Returns audio/mpeg bytes that can be played directly in browser.
    
    Requires:
    - ELEVENLABS_API_KEY in environment
    - ELEVENLABS_VOICE_ID in environment (optional, has default)
    """
    try:
        if not request.text or not request.text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text cannot be empty"
            )
        
        # Get configuration at runtime
        api_key, voice_id = get_elevenlabs_config_runtime()
        
        if not api_key:
            logger.error("ELEVENLABS_API_KEY not found in environment")
            logger.error(f"Environment check: settings={bool(getattr(settings, 'ELEVENLABS_API_KEY', None))}, "
                        f"os.environ={bool(os.environ.get('ELEVENLABS_API_KEY'))}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="TTS service not configured. ELEVENLABS_API_KEY is missing from environment. "
                       "Please set it in .env file and restart the server."
            )
        
        # Call ElevenLabs TTS API
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": request.text.strip(),
            "model_id": "eleven_turbo_v2_5",  # Free tier compatible model
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }
        
        logger.info(f"Calling ElevenLabs TTS API: {url}")
        logger.info(f"Text length: {len(request.text.strip())} chars")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                error_detail = response.text[:200]  # Limit error text
                logger.error(f"ElevenLabs API error: {response.status_code}")
                logger.error(f"Error response: {error_detail}")
                
                # Return helpful error messages
                if response.status_code == 401:
                    detail = "Invalid ElevenLabs API key. Please check your ELEVENLABS_API_KEY configuration."
                elif response.status_code == 429:
                    detail = "ElevenLabs API rate limit exceeded. Please wait and try again."
                elif response.status_code == 422:
                    detail = f"Invalid request to ElevenLabs API: {error_detail}"
                else:
                    detail = f"TTS service error (HTTP {response.status_code}). Check backend logs for details."
                
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=detail
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"TTS service error: {response.status_code}"
                )
            
            # Return audio as streaming response
            audio_bytes = response.content
            
            return StreamingResponse(
                iter([audio_bytes]),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "inline; filename=tts.mp3",
                    "Cache-Control": "no-cache"
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in voice_tts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS conversion failed: {str(e)}"
        )
