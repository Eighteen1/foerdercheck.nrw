from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import os
import logging
from jose import jwt, JWTError
from supabase import create_client, Client, AsyncClient

from . import models, database, email_service
from .database import engine, get_db, Base
from .routes import forms

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Eligibility Check API")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: AsyncClient = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.supabase.co",
        "https://foerdercheck-nrw-frontend.vercel.app",
        "https://foerdercheck-nrw-frontend.vercel.app/*"
    ],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Initialize email service
email_service = email_service.EmailService()

# Supabase JWT verification
async def verify_supabase_jwt(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    
    token = auth_header.split(" ")[1]
    try:
        # Verify the JWT token using Supabase's JWT secret
        payload = jwt.decode(
            token,
            os.getenv("SUPABASE_JWT_SECRET"),
            algorithms=["HS256"]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Base eligibility criteria for households without kids
ELIGIBILITY_CRITERIA_NO_KIDS = {
    1: {  # Single adult
        "base": {"grossA": 38011, "netA": 23540, "grossB": 52724, "netB": 32956},
        "retired": {"grossA": 31076, "netA": 23540, "grossB": 40911, "netB": 32956}
    },
    2: {  # Two adults
        "base": {"grossA": 51777, "netA": 28350, "grossB": 69496, "netB": 39690},
        "retired": {"grossA": 42668, "netA": 28350, "grossB": 56244, "netB": 39690}
    }
}

# Base eligibility criteria for households with kids (1 or more)
ELIGIBILITY_CRITERIA_WITH_KIDS = {
    1: {  # Single adult with kids
        "base": {"grossA": 53121, "netA": 29210, "grossB": 71377, "netB": 40894},
        "retired": {"grossA": 31076, "netA": 23540, "grossB": 40911, "netB": 32956}
    },
    2: {  # Two adults with kids
        "base": {"grossA": 57074, "netA": 35740, "grossB": 79411, "netB": 50036},
        "retired": {"grossA": 42668, "netA": 28350, "grossB": 56244, "netB": 39690}
    }
}

# Child bonus amounts per ADDITIONAL child (beyond the first)
CHILD_BONUS = {
    "single": {  # Single parent household
        "grossA": 5297,   # Group A gross increase per additional child
        "netA": 7390,     # Group A net increase per additional child
        "grossB": 9916,   # Group B gross increase per additional child
        "netB": 10346     # Group B net increase per additional child
    },
    "couple": {  # Two-parent household
        "grossA": 11547,  # Group A gross increase per additional child
        "netA": 7390,     # Group A net increase per additional child
        "grossB": 16166,  # Group B gross increase per additional child
        "netB": 10346     # Group B net increase per additional child
    }
}

# Marriage bonus
MARRIAGE_BONUS = 6250

# Pydantic models for request/response
class EmailRequest(BaseModel):
    email: EmailStr

class TokenResponse(BaseModel):
    message: str

class VerificationResponse(BaseModel):
    message: str

class EligibilityRequest(BaseModel):
    adultCount: int
    childCount: int
    isDisabled: bool
    isMarried: bool
    isRetired: bool
    grossIncome: float
    netIncome: float

class DocumentCheckState(BaseModel):
    propertyType: str
    answers: dict

class StoreEligibilityRequest(BaseModel):
    userId: str
    eligibilityData: Dict[str, Any]

def calculate_limits(request: EligibilityRequest) -> Dict[str, float]:
    # Determine which base criteria to use based on whether there are kids
    if request.childCount == 0:
        base = ELIGIBILITY_CRITERIA_NO_KIDS[request.adultCount]["retired" if request.isRetired else "base"]
        child_gross_bonus_a = 0
        child_net_bonus_a = 0
        child_gross_bonus_b = 0
        child_net_bonus_b = 0
    else:
        base = ELIGIBILITY_CRITERIA_WITH_KIDS[request.adultCount]["retired" if request.isRetired else "base"]
        # Calculate bonus only for additional children beyond the first
        additional_children = max(0, request.childCount - 1)
        # Use different bonus amounts based on whether it's a single parent or couple
        bonus_type = "single" if request.adultCount == 1 else "couple"
        child_gross_bonus_a = additional_children * CHILD_BONUS[bonus_type]["grossA"]
        child_net_bonus_a = additional_children * CHILD_BONUS[bonus_type]["netA"]
        child_gross_bonus_b = additional_children * CHILD_BONUS[bonus_type]["grossB"]
        child_net_bonus_b = additional_children * CHILD_BONUS[bonus_type]["netB"]
    
    # Add marriage bonus to gross income if applicable
    marriage_bonus = MARRIAGE_BONUS if request.isMarried else 0
    
    return {
        "grossA": base["grossA"] + child_gross_bonus_a + marriage_bonus,
        "netA": base["netA"] + child_net_bonus_a,
        "grossB": base["grossB"] + child_gross_bonus_b + marriage_bonus,
        "netB": base["netB"] + child_net_bonus_b
    }

def determine_eligibility(request: EligibilityRequest) -> Dict[str, Any]:
    print("\n=== Starting Eligibility Check ===")
    print(f"Input values:")
    print(f"- Adults: {request.adultCount}")
    print(f"- Children: {request.childCount}")
    print(f"- Gross Income: {request.grossIncome}")
    print(f"- Net Income: {request.netIncome}")
    print(f"- Married: {request.isMarried}")
    print(f"- Retired: {request.isRetired}")

    # Input validation
    if request.adultCount not in [1, 2] or request.childCount < 0:
        print("❌ Invalid input data")
        return {
            "eligible": False,
            "group": "Nicht Förderungsfähig",
            "reason": "Ungültige Eingabedaten. Bitte überprüfen Sie Ihre Angaben.",
            "details": {
                "adjustedGrossA": 0,
                "adjustedNetA": 0,
                "adjustedGrossB": 0,
                "adjustedNetB": 0,
                "childBonus": {"grossA": 0, "netA": 0, "grossB": 0, "netB": 0}
            }
        }

    # Validate income values
    if request.grossIncome <= 0 or request.netIncome <= 0:
        print("❌ Invalid income values (less than or equal to 0)")
        return {
            "eligible": False,
            "group": "Nicht Förderungsfähig",
            "reason": "Das Einkommen muss größer als 0 sein.",
            "details": {
                "adjustedGrossA": 0,
                "adjustedNetA": 0,
                "adjustedGrossB": 0,
                "adjustedNetB": 0,
                "childBonus": {"grossA": 0, "netA": 0, "grossB": 0, "netB": 0}
            }
        }

    # Calculate adjusted limits
    limits = calculate_limits(request)
    print("\nCalculated limits:")
    print(f"Group A limits:")
    print(f"- Gross: {limits['grossA']:.2f}")
    print(f"- Net: {limits['netA']:.2f}")
    print(f"Group B limits:")
    print(f"- Gross: {limits['grossB']:.2f}")
    print(f"- Net: {limits['netB']:.2f}")
    
    # Calculate child bonuses for response (only for additional children)
    additional_children = max(0, request.childCount - 1) if request.childCount > 0 else 0
    child_bonus = {
        "grossA": additional_children * CHILD_BONUS["single"]["grossA"],
        "netA": additional_children * CHILD_BONUS["single"]["netA"],
        "grossB": additional_children * CHILD_BONUS["single"]["grossB"],
        "netB": additional_children * CHILD_BONUS["single"]["netB"]
    }

    # First check if income is within Group A limits
    print("\nChecking if income is within Group A limits:")
    print(f"Gross income {request.grossIncome:.2f} <= {limits['grossA']:.2f}?")
    print(f"Net income {request.netIncome:.2f} <= {limits['netA']:.2f}?")
    
    # Compare as doubles with 2 decimal places
    gross_within_a = request.grossIncome <= limits["grossA"]
    net_within_a = request.netIncome <= limits["netA"]
    
    print(f"Comparing as doubles:")
    print(f"Gross: {request.grossIncome:.2f} <= {limits['grossA']:.2f}? {gross_within_a}")
    print(f"Net: {request.netIncome:.2f} <= {limits['netA']:.2f}? {net_within_a}")
    
    if gross_within_a and net_within_a:
        print("✅ Income within Group A limits")
        return {
            "eligible": True,
            "group": "Gruppe A",
            "reason": "Sie erfüllen die Voraussetzungen für Gruppe A.",
            "details": {
                "adjustedGrossA": limits["grossA"],
                "adjustedNetA": limits["netA"],
                "adjustedGrossB": limits["grossB"],
                "adjustedNetB": limits["netB"],
                "childBonus": child_bonus
            }
        }
    else:
        print("❌ Income exceeds Group A limits")
        if not gross_within_a:
            print(f"- Gross income {request.grossIncome:.2f} exceeds Group A limit of {limits['grossA']:.2f}")
        if not net_within_a:
            print(f"- Net income {request.netIncome:.2f} exceeds Group A limit of {limits['netA']:.2f}")

    # Then check if income exceeds Group B limits (not eligible)
    print("\nChecking if income exceeds Group B limits:")
    print(f"Gross income {request.grossIncome:.2f} > {limits['grossB']:.2f}?")
    print(f"Net income {request.netIncome:.2f} > {limits['netB']:.2f}?")
    
    if request.grossIncome > limits["grossB"] or request.netIncome > limits["netB"]:
        print("❌ Income exceeds Group B limits")
        # Determine the specific reason for ineligibility
        if request.grossIncome > limits["grossB"] and request.netIncome > limits["netB"]:
            reason = "Ihr Brutto- und Nettoeinkommen liegen über den zulässigen Grenzen."
            print("- Both gross and net income exceed limits")
        elif request.grossIncome > limits["grossB"]:
            reason = "Ihr Bruttoeinkommen liegt über der zulässigen Grenze."
            print("- Gross income exceeds limit")
        else:
            reason = "Ihr Nettoeinkommen liegt über der zulässigen Grenze."
            print("- Net income exceeds limit")

        return {
            "eligible": False,
            "group": "Nicht Förderungsfähig",
            "reason": reason,
            "details": {
                "adjustedGrossA": limits["grossA"],
                "adjustedNetA": limits["netA"],
                "adjustedGrossB": limits["grossB"],
                "adjustedNetB": limits["netB"],
                "childBonus": child_bonus
            }
        }
    
    # If we get here, income must be within Group B limits
    print("✅ Income within Group B limits")
    return {
        "eligible": True,
        "group": "Gruppe B",
        "reason": "Sie erfüllen die Voraussetzungen für Gruppe B.",
        "details": {
            "adjustedGrossA": limits["grossA"],
            "adjustedNetA": limits["netA"],
            "adjustedGrossB": limits["grossB"],
            "adjustedNetB": limits["netB"],
            "childBonus": child_bonus
        }
    }

@app.post("/api/check-eligibility")
async def check_eligibility(request: EligibilityRequest):
    try:
        return determine_eligibility(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Eligibility Check API is running"}

@app.post("/api/document-check/save")
async def save_document_check(
    state: DocumentCheckState,
    payload: dict = Depends(verify_supabase_jwt)
):
    try:
        # Get user email from JWT payload
        user_email = payload.get("email")
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Save the document check state
        db = next(get_db())
        user = db.query(models.User).filter(models.User.email == user_email).first()
        
        if not user:
            # Create new user if not found
            user = models.User(
                email=user_email,
                is_verified=True  # Supabase handles email verification
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        user.document_check_state = state.dict()
        db.commit()
        
        return {"message": "Document check state saved successfully"}
    except Exception as e:
        logger.error(f"Error saving document check state: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document check state"
        )

@app.get("/api/document-check/load")
async def load_document_check(payload: dict = Depends(verify_supabase_jwt)):
    try:
        # Get user email from JWT payload
        user_email = payload.get("email")
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        db = next(get_db())
        user = db.query(models.User).filter(models.User.email == user_email).first()
        
        if not user:
            return {"propertyType": "", "answers": {}}

        if not user.document_check_state:
            return {"propertyType": "", "answers": {}}

        return user.document_check_state
    except Exception as e:
        logger.error(f"Error loading document check state: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load document check state"
        )

@app.post("/api/user/create")
async def create_user(request: EmailRequest):
    try:
        logger.info(f"Creating user with email: {request.email}")
        
        # Create user in Supabase Auth using admin API
        auth_response = supabase.auth.admin.create_user({
            "email": request.email,
            "email_confirm": True,
            "user_metadata": {
                "created_via": "foerdercheck"
            },
            "app_metadata": {
                "provider": "email"
            }
        })
        
        logger.info(f"Auth response: {auth_response}")
        
        if not auth_response or not auth_response.user:
            logger.error("No user data in auth response")
            raise HTTPException(status_code=400, detail="Failed to create user: No user data in response")
        
        # Create initial user_data record
        user_data_response = supabase.table('user_data').insert({
            "id": auth_response.user.id,
            "eligibility_data": None,
            "application_status": "pending",
            "document_status": {},
            "created_at": datetime.now().isoformat()
        }).execute()
        
        logger.info(f"User data response: {user_data_response}")
        
        # Check if the response contains data
        if not user_data_response.data:
            logger.error("No data returned from user_data creation")
            raise HTTPException(status_code=400, detail="Failed to create user data record")
        
        logger.info(f"Successfully created user and user_data for email: {request.email}")
        
        return {
            "message": "User created successfully",
            "user": {
                "id": auth_response.user.id,
                "email": request.email
            }
        }
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/user/store-eligibility")
async def store_eligibility_data(request: StoreEligibilityRequest):
    try:
        logger.info(f"Storing eligibility data for user: {request.userId}")
        
        # Update user_data record with eligibility data
        response = supabase.table('user_data').update({
            "eligibility_data": request.eligibilityData,
            "updated_at": datetime.now().isoformat()
        }).eq("id", request.userId).execute()
        
        if response.error:
            logger.error(f"Error storing eligibility data: {response.error}")
            raise HTTPException(status_code=400, detail=str(response.error))
        
        return {"message": "Eligibility data stored successfully"}
    except Exception as e:
        logger.error(f"Error storing eligibility data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/test")
async def test_endpoint():
    logger.info("Test endpoint hit")
    return {"message": "User controller is working"}

# Include routers
app.include_router(forms.router) 