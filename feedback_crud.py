from sqlalchemy.orm import Session
import models
import schemas
from typing import List, Optional

def create_feedback(db: Session, feedback: schemas.FeedbackCreate):
    db_feedback = models.Feedback(**feedback.dict())
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

def get_feedback_by_student(db: Session, student_id: int):
    return db.query(models.Feedback).filter(models.Feedback.student_id == student_id).all()

def get_feedback_by_internship(db: Session, internship_id: int):
    return db.query(models.Feedback).filter(models.Feedback.internship_id == internship_id).all()

def get_feedback_by_mentor(db: Session, mentor_id: int):
    return db.query(models.Feedback).filter(models.Feedback.mentor_id == mentor_id).all()

def update_feedback(db: Session, feedback_id: int, feedback_update: schemas.FeedbackUpdate):
    feedback = db.query(models.Feedback).filter(models.Feedback.id == feedback_id).first()
    if feedback:
        update_data = feedback_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(feedback, field, value)
        db.commit()
        db.refresh(feedback)
    return feedback