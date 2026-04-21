from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.db.models import CVDocument, JDDocument, MatchHistory, RefreshToken, User


@dataclass
class MatchListItem:
    id: int
    similarity_score: float | None
    created_at: object
    cv_title: str
    jd_title: str


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def exists(self, user_id: int) -> bool:
        return self.get_by_id(user_id) is not None

    def update_profile(
        self,
        user: User,
        *,
        full_name: str | None,
        phone: str | None,
        headline: str | None,
        bio: str | None,
    ) -> User:
        user.full_name = full_name
        user.phone = phone
        user.headline = headline
        user.bio = bio
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_avatar(self, user: User, avatar_path: str | None) -> User:
        user.avatar_path = avatar_path
        self.db.commit()
        self.db.refresh(user)
        return user


class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, *, user_id: int, token_hash: str, expires_at) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_active(self, *, user_id: int, token_hash: str) -> RefreshToken | None:
        return self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
        ).first()

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash
        ).first()

    def revoke(self, token: RefreshToken) -> None:
        token.is_revoked = True
        self.db.commit()

    def revoke_all_for_user(self, user_id: int) -> None:
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,
        ).update({"is_revoked": True})
        self.db.commit()


class CVRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        title: str,
        original_filename: str,
        storage_path: str,
        content_text: str,
    ) -> CVDocument:
        record = CVDocument(
            user_id=user_id,
            title=title,
            original_filename=original_filename,
            storage_path=storage_path,
            content_text=content_text,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_by_user(self, user_id: int) -> list[CVDocument]:
        return self.db.query(CVDocument).filter(
            CVDocument.user_id == user_id
        ).order_by(CVDocument.created_at.desc()).all()

    def get_for_user(self, cv_id: int, user_id: int) -> CVDocument | None:
        return self.db.query(CVDocument).filter(
            CVDocument.id == cv_id,
            CVDocument.user_id == user_id,
        ).first()

    def delete(self, record: CVDocument) -> None:
        self.db.delete(record)
        self.db.commit()


class JDRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        title: str,
        original_filename: str,
        storage_path: str,
        content_text: str,
    ) -> JDDocument:
        record = JDDocument(
            user_id=user_id,
            title=title,
            original_filename=original_filename,
            storage_path=storage_path,
            content_text=content_text,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_by_user(self, user_id: int) -> list[JDDocument]:
        return self.db.query(JDDocument).filter(
            JDDocument.user_id == user_id
        ).order_by(JDDocument.created_at.desc()).all()

    def get_for_user(self, jd_id: int, user_id: int) -> JDDocument | None:
        return self.db.query(JDDocument).filter(
            JDDocument.id == jd_id,
            JDDocument.user_id == user_id,
        ).first()

    def delete(self, record: JDDocument) -> None:
        self.db.delete(record)
        self.db.commit()


class MatchRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        cv_id: int,
        jd_id: int,
        similarity_score: float,
        report_json: str,
    ) -> MatchHistory:
        record = MatchHistory(
            user_id=user_id,
            cv_id=cv_id,
            jd_id=jd_id,
            similarity_score=similarity_score,
            report_json=report_json,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_for_user(self, match_id: int, user_id: int) -> MatchHistory | None:
        return self.db.query(MatchHistory).filter(
            MatchHistory.id == match_id,
            MatchHistory.user_id == user_id,
        ).first()

    def delete(self, record: MatchHistory) -> None:
        self.db.delete(record)
        self.db.commit()

    def delete_for_cv(self, cv_id: int, user_id: int) -> None:
        self.db.query(MatchHistory).filter(
            MatchHistory.cv_id == cv_id,
            MatchHistory.user_id == user_id,
        ).delete(synchronize_session=False)
        self.db.commit()

    def delete_for_jd(self, jd_id: int, user_id: int) -> None:
        self.db.query(MatchHistory).filter(
            MatchHistory.jd_id == jd_id,
            MatchHistory.user_id == user_id,
        ).delete(synchronize_session=False)
        self.db.commit()

    def count_by_user(self, user_id: int) -> int:
        return self.db.query(MatchHistory).filter(
            MatchHistory.user_id == user_id
        ).count()

    def list_by_user(self, user_id: int, *, limit: int, offset: int) -> list[MatchListItem]:
        rows = self.db.query(
            MatchHistory.id,
            MatchHistory.similarity_score,
            MatchHistory.created_at,
            CVDocument.title.label("cv_title"),
            JDDocument.title.label("jd_title"),
        ).join(
            CVDocument, MatchHistory.cv_id == CVDocument.id
        ).join(
            JDDocument, MatchHistory.jd_id == JDDocument.id
        ).filter(
            MatchHistory.user_id == user_id
        ).order_by(
            MatchHistory.created_at.desc()
        ).offset(offset).limit(limit).all()

        return [
            MatchListItem(
                id=row.id,
                similarity_score=row.similarity_score,
                created_at=row.created_at,
                cv_title=row.cv_title,
                jd_title=row.jd_title,
            )
            for row in rows
        ]
