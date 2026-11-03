from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..logbook import write_log
from ..models import User
from ..schemas import LoginRequest, Message, Token, UserOut, UserRegister
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario ya existe")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El email ya esta registrado")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        can_read=True,
        can_write=False,
        can_update=False,
        is_admin=False,
    )
    db.add(user)
    db.flush()

    write_log(db, action="REGISTER", username=user.username, resource=f"user:{user.id}")
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()

    if user is None or not verify_password(payload.password, user.hashed_password):
        write_log(
            db,
            action="LOGIN",
            username=payload.username,
            result="FAIL",
            details="Credenciales incorrectas",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contrasena incorrectos",
        )

    token = create_access_token({"sub": user.username})
    write_log(db, action="LOGIN", username=user.username, result="OK")
    db.commit()
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", response_model=Message)
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    write_log(db, action="LOGOUT", username=current_user.username, result="OK")
    db.commit()
    return Message(detail="Sesion cerrada")
