from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import os
import logging

from . import models, database, email_service
from .database import engine, get_db
from .routes import forms

app = FastAPI(title="Eligibility Check API")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.supabase.co"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Initialize email service
email_service = email_service.EmailService()

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

# Authentication endpoints
@app.post("/api/auth/register", response_model=TokenResponse)
async def register(request: EmailRequest, db: Session = Depends(get_db)):
    logger.info(f"Registration attempt for email: {request.email}")
    
    # Check if user already exists
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if user:
        logger.info(f"User already exists: {request.email}")
        if user.is_verified:
            logger.warning(f"User already verified: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered and verified"
            )
        # If user exists but is not verified, generate new verification token
        token = user.generate_auth_token()
        logger.info(f"Generated new verification token for existing user: {request.email}")
        db.commit()
    else:
        # Create new user
        logger.info(f"Creating new user: {request.email}")
        user = models.User(email=request.email)
        token = user.generate_auth_token()
        logger.info(f"Generated verification token for new user: {request.email}")
        db.add(user)
        db.commit()

    # Send verification email
    if email_service.send_verification_email(request.email, token):
        logger.info(f"Verification email sent to: {request.email}")
        return {"message": "Verification email sent"}
    else:
        logger.error(f"Failed to send verification email to: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: EmailRequest, db: Session = Depends(get_db)):
    logger.info(f"Login attempt for email: {request.email}")
    
    user = db.query(models.User).filter(models.User.email == request.email).first()
    
    if not user:
        logger.warning(f"Login failed - user not found: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_verified:
        logger.warning(f"Login failed - user not verified: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please verify your email first"
        )

    # Generate new login token
    token = user.generate_auth_token()
    logger.info(f"Generated login token for user: {request.email}")
    db.commit()

    # Send login link
    if email_service.send_login_link(request.email, token):
        logger.info(f"Login link sent to: {request.email}")
        return {"message": "Login link sent"}
    else:
        logger.error(f"Failed to send login link to: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send login link"
        )

@app.get("/api/auth/verify/{token}", response_model=VerificationResponse)
async def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        # First check if token exists and is valid
        user = db.query(models.User).filter(models.User.auth_token == token).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ungültiger oder abgelaufener Token"
            )

        # Check if token is expired
        if user.token_expires_at and user.token_expires_at < datetime.utcnow():
            # Clear the expired token
            user.auth_token = None
            user.token_expires_at = None
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token ist abgelaufen"
            )

        # Update user verification status
        user.is_verified = True
        user.auth_token = None
        user.token_expires_at = None
        user.last_login = datetime.utcnow()
        
        try:
            db.commit()
            return {"message": "E-Mail erfolgreich bestätigt"}
        except Exception as db_error:
            db.rollback()
            print(f"Database error during verification: {str(db_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ein Fehler ist bei der Datenbankoperation aufgetreten"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error during verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ein unerwarteter Fehler ist aufgetreten"
        )

@app.get("/api/auth/login/{token}")
async def login_with_token(token: str, db: Session = Depends(get_db)):
    try:
        user = db.query(models.User).filter(models.User.auth_token == token).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ungültiger oder abgelaufener Login-Link"
            )

        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bitte bestätigen Sie zuerst Ihre E-Mail-Adresse"
            )

        if user.token_expires_at and user.token_expires_at < datetime.utcnow():
            # Clear the expired token
            user.auth_token = None
            user.token_expires_at = None
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Login-Link ist abgelaufen"
            )

        # Generate a new session token
        session_token = user.generate_auth_token()
        
        # Update last login and clear the old token
        user.last_login = datetime.utcnow()
        user.auth_token = None
        user.token_expires_at = None
        
        try:
            db.commit()
            return {
                "message": "Erfolgreich eingeloggt",
                "email": user.email,
                "token": session_token
            }
        except Exception as db_error:
            db.rollback()
            logger.error(f"Database error during login: {str(db_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ein Fehler ist bei der Datenbankoperation aufgetreten"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ein unerwarteter Fehler ist aufgetreten"
        )

def get_token_from_header(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    return auth_header.split(" ")[1]

@app.get("/api/auth/validate")
async def validate_token(token: str = Depends(get_token_from_header), db: Session = Depends(get_db)):
    try:
        user = db.query(models.User).filter(models.User.auth_token == token).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        if user.token_expires_at and user.token_expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )

        return {"valid": True, "email": user.email}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token validation failed"
        )

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
    token: str = Depends(get_token_from_header),
    db: Session = Depends(get_db)
):
    try:
        # First try to find user by token
        user = db.query(models.User).filter(models.User.auth_token == token).first()
        
        if not user:
            # If no user found with token, try to find by email in token
            try:
                # Decode token to get email (assuming token contains email)
                email = token  # In this case, token is the email
                user = db.query(models.User).filter(models.User.email == email).first()
                
                if not user:
                    # Create new user if not found
                    user = models.User(
                        email=email,
                        auth_token=token,
                        token_expires_at=datetime.utcnow() + timedelta(days=30)  # Extend token expiry
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
            except Exception as e:
                logger.error(f"Error processing token: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )

        # Save the document check state
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
async def load_document_check(
    token: str = Depends(get_token_from_header),
    db: Session = Depends(get_db)
):
    try:
        # First try to find user by token
        user = db.query(models.User).filter(models.User.auth_token == token).first()
        
        if not user:
            # If no user found with token, try to find by email in token
            try:
                # Decode token to get email (assuming token contains email)
                email = token  # In this case, token is the email
                user = db.query(models.User).filter(models.User.email == email).first()
                
                if not user:
                    # Create new user if not found
                    user = models.User(
                        email=email,
                        auth_token=token,
                        token_expires_at=datetime.utcnow() + timedelta(days=30)  # Extend token expiry
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
            except Exception as e:
                logger.error(f"Error processing token: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )

        if not user.document_check_state:
            return {"propertyType": "", "answers": {}}

        return user.document_check_state
    except Exception as e:
        logger.error(f"Error loading document check state: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load document check state"
        )

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(forms.router) 