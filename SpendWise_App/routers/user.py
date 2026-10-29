import secrets

from fastapi import Response, status, HTTPException, Depends, APIRouter
from typing import Annotated

from fastapi.responses import HTMLResponse
from ..routers.settings import create_default_settings
from ..utils.utils import get_or_create_budget
from ..utils.auth import get_password_hash, verify_password
from ..utils.email import send_email_change_verification, send_verification_email, send_password_reset_email, generate_verification_code, generate_reset_code, get_verification_code_expiry, get_reset_token_expiry, send_password_changed_notification, hash_one_time_code, verify_one_time_code
from ..models import *
from ..oauth2 import get_current_active_user, get_user
from ..database import *
from datetime import datetime, timezone
from sqlmodel import select

router = APIRouter(
    prefix="/users",
    tags=['Users']
)

CurrentUser = Annotated[UserDetails, Depends(get_current_active_user)]
MAX_ONE_TIME_CODE_ATTEMPTS = 5


def _clear_one_time_code(user: UserDetails, code_field: str, expiry_field: str, attempts_field: str) -> None:
    setattr(user, code_field, None)
    setattr(user, expiry_field, None)
    setattr(user, attempts_field, 0)


def _one_time_code_expired(expiry: datetime | None) -> bool:
    if expiry is None:
        return True
    expiry_utc = expiry if expiry.tzinfo else expiry.replace(tzinfo=timezone.utc)
    return expiry_utc <= datetime.now(timezone.utc)


def _reject_one_time_code(db: SessionDependency, user: UserDetails, code_field: str, expiry_field: str,
                          attempts_field: str, invalid_detail: str, limit_detail: str) -> None:
    attempts = (getattr(user, attempts_field) or 0) + 1
    if attempts >= MAX_ONE_TIME_CODE_ATTEMPTS:
        _clear_one_time_code(user, code_field, expiry_field, attempts_field)
        db.add(user)
        db.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=limit_detail)

    setattr(user, attempts_field, attempts)
    db.add(user)
    db.commit()
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=invalid_detail)


def _reject_expired_one_time_code(db: SessionDependency, user: UserDetails, code_field: str,
                                 expiry_field: str, attempts_field: str, detail: str) -> None:
    _clear_one_time_code(user, code_field, expiry_field, attempts_field)
    db.add(user)
    db.commit()
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register_user(user: UserCreate, db: SessionDependency):
    existing_user = get_user(db, email=user.Email)

    # existing (not yet verified code) user
    if existing_user:
        # If they are already verified, we throw the usual error
        if existing_user.EmailVerified:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # If they exist but ARE NOT verified (the "stuck" state):
        # We update their info and send a new code (effectively a "resend")
        existing_user.HashedPassword = get_password_hash(user.Password)
        verification_code = generate_verification_code()
        existing_user.VerificationCode = hash_one_time_code(verification_code, "email-verification")
        existing_user.VerificationCodeExpiry = get_verification_code_expiry()
        existing_user.VerificationCodeFailedAttempts = 0

        db.add(existing_user)
        db.commit()
        db.refresh(existing_user)

        # Send the new verification email
        email_sent = send_verification_email(user.Email, verification_code)
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email. Please try again."
            )

        return existing_user

    # new user flow
    hashed_pw = get_password_hash(user.Password)
    
    # Generate verification code
    verification_code = generate_verification_code()

    new_user = UserDetails(
        Email=user.Email,
        HashedPassword=hashed_pw,
        UserType="user",
        Active=False,  # User is inactive until email is verified
        EmailVerified=False,
        VerificationCode=hash_one_time_code(verification_code, "email-verification"),
        VerificationCodeExpiry=get_verification_code_expiry(),
        VerificationCodeFailedAttempts=0
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Send verification email
    email_sent = send_verification_email(user.Email, verification_code)
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again."
        )

    return new_user

# delete account and related tables (cascade)
@router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_account(payload: UserDeleteAccount, current_user: CurrentUser,db: SessionDependency):
    # 1. Validation Check
    if not (payload.IsSure and payload.DataDelete):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must confirm account and data deletion."
        )

    # 2. Password Verification
    if not verify_password(payload.Password, current_user.HashedPassword):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, # <-- The Fix
            detail="The password you entered is incorrect."
        )

    db.delete(current_user)
    db.commit()
    
    return None # 204 No Content typically returns nothing

# prompt user for current password before changing password
@router.put("/verify-password", status_code=status.HTTP_202_ACCEPTED, response_model=UserResponse)
def verify_user_password(payload: UserVerifyPassword, current_user: CurrentUser, db: SessionDependency):
    # 1. Verify the provided current password against the stored hash
    is_valid = verify_password(payload.Password, current_user.HashedPassword)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The password you entered is incorrect."
        )

    return current_user

# change password and update databse
@router.put("/change-password", status_code=status.HTTP_202_ACCEPTED, response_model=UserResponse)
def change_user_password(payload: UserChangePassword, current_user: CurrentUser, db: SessionDependency):
    if not verify_password(payload.CurrentPassword, current_user.HashedPassword):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The current password is incorrect."
        )

    new_pw = payload.Password
    re_new_pw = payload.RePassword

    if not new_pw == re_new_pw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The passwords do not match."
        )
    
    hashed_new_pw = get_password_hash(new_pw)
    current_user.HashedPassword = hashed_new_pw
    current_user.RefreshToken = None

    lock_token = secrets.token_urlsafe(32)
    current_user.LockToken = lock_token

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    # Trigger the security email in the background
    send_password_changed_notification(current_user.Email, lock_token)

    return current_user

# Verify email after registration
@router.post("/verify-email", status_code=status.HTTP_200_OK)
def verify_email(payload: VerifyEmailRequest, db: SessionDependency):
    """User submits their email and verification code"""
    
    # 1. Find the user
    user = get_user(db, email=payload.Email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 2. Check if already verified
    if user.EmailVerified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    if not user.VerificationCode:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No active verification code. Request a new one.")

    # Expiry remains enforced; expired values are cleared from the account.
    if _one_time_code_expired(user.VerificationCodeExpiry):
        _reject_expired_one_time_code(db, user, "VerificationCode", "VerificationCodeExpiry",
                                      "VerificationCodeFailedAttempts", "Verification code expired. Request a new one.")

    if not verify_one_time_code(payload.VerificationCode, user.VerificationCode, "email-verification"):
        _reject_one_time_code(db, user, "VerificationCode", "VerificationCodeExpiry",
                              "VerificationCodeFailedAttempts", "Invalid verification code",
                              "Too many incorrect attempts. Request a new verification code.")
    
    # 5. Mark email as verified and activate user
    user.EmailVerified = True
    user.Active = True
    _clear_one_time_code(user, "VerificationCode", "VerificationCodeExpiry", "VerificationCodeFailedAttempts")
    
    create_default_settings(db, user.Id)
    get_or_create_budget(user.Id, db)

    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"detail": "Email verified successfully. You can now log in."}


# Request password reset
@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(payload: ForgotPasswordRequest, db: SessionDependency):
    """User requests password reset by providing their email"""
    
    # 1. Find the user
    user = get_user(db, email=payload.Email)
    if not user:
        # Don't reveal if email exists (security best practice)
        return {"detail": "If this email exists, you will receive a password reset code"}
    
    # 2. Generate reset token/code
    reset_code = generate_reset_code()
    
    # 3. Save hashed version and expiry to DB
    user.ResetToken = hash_one_time_code(reset_code, "password-reset")
    user.ResetTokenExpiry = get_reset_token_expiry()
    user.ResetTokenFailedAttempts = 0
    
    db.add(user)
    db.commit()
    
    # 4. Send email with reset code
    email_sent = send_password_reset_email(payload.Email, reset_code)
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send reset email. Please try again."
        )
    
    return {"detail": "If this email exists, you will receive a password reset code"}


# Reset password with code
@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(payload: ResetPasswordRequest, db: SessionDependency):
    """User resets password using the code from email"""
    
    # 1. Find the user
    user = get_user(db, email=payload.Email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 2. Check if reset token exists
    if not user.ResetToken:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No password reset request found. Please use forgot-password first."
        )
    
    if _one_time_code_expired(user.ResetTokenExpiry):
        _reject_expired_one_time_code(db, user, "ResetToken", "ResetTokenExpiry",
                                      "ResetTokenFailedAttempts", "Reset code expired. Please request a new one.")

    if not verify_one_time_code(payload.ResetCode, user.ResetToken, "password-reset"):
        _reject_one_time_code(db, user, "ResetToken", "ResetTokenExpiry", "ResetTokenFailedAttempts",
                              "Invalid reset code", "Too many incorrect attempts. Request a new reset code.")
    
    # 5. Update password
    new_hashed_pw = get_password_hash(payload.NewPassword)
    user.HashedPassword = new_hashed_pw
    user.RefreshToken = None
    _clear_one_time_code(user, "ResetToken", "ResetTokenExpiry", "ResetTokenFailedAttempts")
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"detail": "Password reset successfully. You can now log in with your new password."}

# Request Email Change
@router.post("/request-email-change", status_code=status.HTTP_200_OK)
def request_email_change(payload: RequestEmailChange, current_user: CurrentUser, db: SessionDependency):
    """Verifies password and sends a code to the NEW email address."""
    
    # 1. Security Check: Verify current password
    if not verify_password(payload.Password, current_user.HashedPassword):
        raise HTTPException(status_code=400, detail="Incorrect password.")
        
    # 2. Prevent redundant changes
    if payload.NewEmail.lower() == current_user.Email.lower():
        raise HTTPException(status_code=400, detail="This is already your current email address.")
        
    # 3. Check if the new email is already taken by another account
    email_taken = get_user(db, email=payload.NewEmail)
    if email_taken:
        raise HTTPException(status_code=400, detail="This email is already associated with another account.")
        
    # 4. Generate Code and Update State
    code = generate_verification_code()
    current_user.PendingEmail = payload.NewEmail
    current_user.VerificationCode = hash_one_time_code(code, "email-verification")
    current_user.VerificationCodeExpiry = get_verification_code_expiry()
    current_user.VerificationCodeFailedAttempts = 0
    
    db.add(current_user)
    db.commit()
    
    # 5. Send Email to the NEW address
    email_sent = send_email_change_verification(payload.NewEmail, code)
    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send verification email.")
        
    return {"detail": "A verification code has been sent to your new email address."}


# Confirm Email Change
@router.post("/confirm-email-change", status_code=status.HTTP_200_OK)
def confirm_email_change(payload: ConfirmEmailChange, current_user: CurrentUser, db: SessionDependency):
    """Validates the code and formally updates the user's email."""
    
    if not current_user.PendingEmail:
        raise HTTPException(status_code=400, detail="No email change request found.")
        
    if not current_user.VerificationCode:
        raise HTTPException(status_code=401, detail="No active verification code. Request a new one.")

    # 1. Validate expiry
    if _one_time_code_expired(current_user.VerificationCodeExpiry):
        _reject_expired_one_time_code(db, current_user, "VerificationCode", "VerificationCodeExpiry",
                                      "VerificationCodeFailedAttempts", "Verification code expired. Please request a new one.")

    # 2. Validate code
    if not verify_one_time_code(payload.VerificationCode, current_user.VerificationCode, "email-verification"):
        _reject_one_time_code(db, current_user, "VerificationCode", "VerificationCodeExpiry",
                              "VerificationCodeFailedAttempts", "Invalid verification code.",
                              "Too many incorrect attempts. Request a new verification code.")
        
    # 3. Apply the Change
    current_user.Email = current_user.PendingEmail
    current_user.PendingEmail = None
    _clear_one_time_code(current_user, "VerificationCode", "VerificationCodeExpiry", "VerificationCodeFailedAttempts")
    
    db.add(current_user)
    db.commit()
    
    return {"detail": "Email successfully updated!"}

@router.get("/lock-account/{token}", response_class=HTMLResponse)
def emergency_lock_account(token: str, db: SessionDependency):
    """Triggered directly when a user clicks the lock link in their email."""
    
    user = db.exec(select(UserDetails).where(UserDetails.LockToken == token)).first()
    
    if not user:
        # Token is invalid or already used
        return """
        <html><body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h2 style="color: #D93D42;">Invalid or Expired Link</h2>
            <p>This account lock link is no longer valid.</p>
        </body></html>
        """
        
    # Freeze the account
    user.Active = False
    
    # Clear the token so it can only be used once
    user.LockToken = None
    
    db.add(user)
    db.commit()
    
    # Return a success page
    return f"""
    <html><body style="font-family: sans-serif; text-align: center; padding: 50px; background-color: #F4F5F8;">
        <div style="max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <h2 style="color: #5C55D9;">Account Locked</h2>
            <p style="color: #333;">Your SpendWise account (<b>{user.Email}</b>) has been successfully frozen to protect your data.</p>
            <p style="color: #666; font-size: 14px;">You will not be able to log in until you contact support to verify your identity.</p>
        </div>
    </body></html>
    """
