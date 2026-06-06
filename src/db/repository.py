from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.models import AppSetting, CVDocument, JDDocument, MatchHistory, RefreshToken, User


@dataclass
class MatchListItem:
    id: int
    similarity_score: float | None
    created_at: object
    cv_title: str
    jd_title: str


@dataclass
class AdminUserListItem:
    id: int
    email: str
    full_name: str | None
    role: str
    plan: str
    premium_until: object | None
    is_active: bool
    is_verified: bool
    created_at: object
    cv_count: int
    jd_count: int
    match_count: int


@dataclass
class AdminMatchListItem:
    id: int
    user_id: int
    user_email: str
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

    def list_users_with_usage(self, *, limit: int, offset: int, search: str | None = None) -> list[AdminUserListItem]:
        cv_counts = self.db.query(
            CVDocument.user_id.label("user_id"),
            func.count(CVDocument.id).label("cv_count"),
        ).group_by(CVDocument.user_id).subquery()
        jd_counts = self.db.query(
            JDDocument.user_id.label("user_id"),
            func.count(JDDocument.id).label("jd_count"),
        ).group_by(JDDocument.user_id).subquery()
        match_counts = self.db.query(
            MatchHistory.user_id.label("user_id"),
            func.count(MatchHistory.id).label("match_count"),
        ).group_by(MatchHistory.user_id).subquery()

        query = self.db.query(
            User.id,
            User.email,
            User.full_name,
            User.role,
            User.plan,
            User.premium_until,
            User.is_active,
            User.is_verified,
            User.created_at,
            func.coalesce(cv_counts.c.cv_count, 0).label("cv_count"),
            func.coalesce(jd_counts.c.jd_count, 0).label("jd_count"),
            func.coalesce(match_counts.c.match_count, 0).label("match_count"),
        ).outerjoin(cv_counts, User.id == cv_counts.c.user_id
        ).outerjoin(jd_counts, User.id == jd_counts.c.user_id
        ).outerjoin(match_counts, User.id == match_counts.c.user_id)

        if search:
            like = f"%{search.strip()}%"
            query = query.filter(User.email.ilike(like))

        rows = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
        return [
            AdminUserListItem(
                id=row.id,
                email=row.email,
                full_name=row.full_name,
                role=row.role,
                plan=row.plan,
                premium_until=row.premium_until,
                is_active=row.is_active,
                is_verified=row.is_verified,
                created_at=row.created_at,
                cv_count=int(row.cv_count or 0),
                jd_count=int(row.jd_count or 0),
                match_count=int(row.match_count or 0),
            )
            for row in rows
        ]

    def count_users(self, *, search: str | None = None) -> int:
        query = self.db.query(User)
        if search:
            query = query.filter(User.email.ilike(f"%{search.strip()}%"))
        return query.count()

    def set_admin_managed_fields(
        self,
        user: User,
        *,
        role: str | None = None,
        plan: str | None = None,
        premium_until: datetime | None = None,
        is_active: bool | None = None,
    ) -> User:
        if role is not None:
            user.role = role
        if plan is not None:
            user.plan = plan
        if premium_until is not None or plan == "free":
            user.premium_until = premium_until
        if is_active is not None:
            user.is_active = is_active
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

    def count_by_user(self, user_id: int) -> int:
        return self.db.query(CVDocument).filter(CVDocument.user_id == user_id).count()

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

    def count_by_user(self, user_id: int) -> int:
        return self.db.query(JDDocument).filter(JDDocument.user_id == user_id).count()

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

    def update_user_review(self, record: MatchHistory, user_review: str | None) -> MatchHistory:
        record.user_review = user_review
        self.db.commit()
        self.db.refresh(record)
        return record

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

    def count_by_user_since(self, user_id: int, since: datetime) -> int:
        return self.db.query(MatchHistory).filter(
            MatchHistory.user_id == user_id,
            MatchHistory.created_at >= since,
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

    def count_all(self, *, user_id: int | None = None, search: str | None = None) -> int:
        query = self.db.query(MatchHistory)
        if search:
            query = query.join(User, MatchHistory.user_id == User.id).filter(
                User.email.ilike(f"%{search.strip()}%")
            )
        if user_id is not None:
            query = query.filter(MatchHistory.user_id == user_id)
        return query.count()

    def list_all(
        self,
        *,
        limit: int,
        offset: int,
        user_id: int | None = None,
        search: str | None = None,
    ) -> list[AdminMatchListItem]:
        query = self.db.query(
            MatchHistory.id,
            MatchHistory.user_id,
            User.email.label("user_email"),
            MatchHistory.similarity_score,
            MatchHistory.created_at,
            CVDocument.title.label("cv_title"),
            JDDocument.title.label("jd_title"),
        ).join(
            User, MatchHistory.user_id == User.id
        ).join(
            CVDocument, MatchHistory.cv_id == CVDocument.id
        ).join(
            JDDocument, MatchHistory.jd_id == JDDocument.id
        )

        if user_id is not None:
            query = query.filter(MatchHistory.user_id == user_id)
        if search:
            query = query.filter(User.email.ilike(f"%{search.strip()}%"))

        rows = query.order_by(MatchHistory.created_at.desc()).offset(offset).limit(limit).all()
        return [
            AdminMatchListItem(
                id=row.id,
                user_id=row.user_id,
                user_email=row.user_email,
                similarity_score=row.similarity_score,
                created_at=row.created_at,
                cv_title=row.cv_title,
                jd_title=row.jd_title,
            )
            for row in rows
        ]

    def get_by_id(self, match_id: int) -> MatchHistory | None:
        return self.db.query(MatchHistory).filter(MatchHistory.id == match_id).first()


class AppSettingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str) -> str | None:
        setting = self.db.query(AppSetting).filter(AppSetting.key == key).first()
        return setting.value if setting else None

    def set(self, key: str, value: str | None) -> AppSetting:
        setting = self.db.query(AppSetting).filter(AppSetting.key == key).first()
        if setting:
            setting.value = value
        else:
            setting = AppSetting(key=key, value=value)
            self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting
