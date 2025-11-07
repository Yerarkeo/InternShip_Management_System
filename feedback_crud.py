from sqlalchemy.orm import Session
import models
import schemas
from typing import List, Optional

# Existing Feedback CRUD Operations
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

# Enhanced Mentor Feedback CRUD Operations
def create_mentor_feedback(db: Session, feedback: schemas.MentorFeedbackCreate, mentor_id: int):
    # Calculate overall rating
    ratings = [
        feedback.technical_rating,
        feedback.communication_rating, 
        feedback.teamwork_rating,
        feedback.problem_solving_rating
    ]
    valid_ratings = [r for r in ratings if r is not None]
    overall_rating = sum(valid_ratings) / len(valid_ratings) if valid_ratings else None
    
    db_feedback = models.MentorFeedback(
        **feedback.dict(),
        mentor_id=mentor_id,
        overall_rating=overall_rating,
        status=models.FeedbackStatus.SUBMITTED
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

def get_mentor_feedback_by_id(db: Session, feedback_id: int):
    return db.query(models.MentorFeedback).filter(models.MentorFeedback.id == feedback_id).first()

def get_mentor_feedbacks_by_mentor(db: Session, mentor_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.MentorFeedback).filter(models.MentorFeedback.mentor_id == mentor_id).offset(skip).limit(limit).all()

def get_mentor_feedbacks_by_student(db: Session, student_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.MentorFeedback).filter(models.MentorFeedback.student_id == student_id).offset(skip).limit(limit).all()

def get_mentor_feedback_by_application(db: Session, application_id: int):
    return db.query(models.MentorFeedback).filter(models.MentorFeedback.application_id == application_id).first()

def get_mentor_feedback_by_internship(db: Session, internship_id: int):
    return db.query(models.MentorFeedback).filter(models.MentorFeedback.internship_id == internship_id).all()

def update_mentor_feedback(db: Session, feedback_id: int, feedback_update: schemas.MentorFeedbackUpdate):
    db_feedback = db.query(models.MentorFeedback).filter(models.MentorFeedback.id == feedback_id).first()
    if not db_feedback:
        return None
    
    update_data = feedback_update.dict(exclude_unset=True)
    
    # Recalculate overall rating if any ratings are updated
    if any(key in update_data for key in ['technical_rating', 'communication_rating', 'teamwork_rating', 'problem_solving_rating']):
        ratings = [
            update_data.get('technical_rating', db_feedback.technical_rating),
            update_data.get('communication_rating', db_feedback.communication_rating),
            update_data.get('teamwork_rating', db_feedback.teamwork_rating),
            update_data.get('problem_solving_rating', db_feedback.problem_solving_rating)
        ]
        valid_ratings = [r for r in ratings if r is not None]
        if valid_ratings:
            update_data['overall_rating'] = sum(valid_ratings) / len(valid_ratings)
    
    for field, value in update_data.items():
        setattr(db_feedback, field, value)
    
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

def delete_mentor_feedback(db: Session, feedback_id: int):
    db_feedback = db.query(models.MentorFeedback).filter(models.MentorFeedback.id == feedback_id).first()
    if db_feedback:
        db.delete(db_feedback)
        db.commit()
    return db_feedback

# Evaluation CRUD Operations
def create_evaluation(db: Session, evaluation: schemas.EvaluationCreate, admin_id: int):
    # Calculate overall score (average of all criteria)
    scores = [
        evaluation.technical_competence,
        evaluation.task_completion,
        evaluation.communication_skills,
        evaluation.professionalism,
        evaluation.initiative
    ]
    overall_score = sum(scores) / len(scores)
    
    db_evaluation = models.Evaluation(
        **evaluation.dict(),
        admin_id=admin_id,
        overall_score=overall_score
    )
    db.add(db_evaluation)
    db.commit()
    db.refresh(db_evaluation)
    return db_evaluation

def get_evaluation_by_id(db: Session, evaluation_id: int):
    return db.query(models.Evaluation).filter(models.Evaluation.id == evaluation_id).first()

def get_evaluations_by_admin(db: Session, admin_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Evaluation).filter(models.Evaluation.admin_id == admin_id).offset(skip).limit(limit).all()

def get_evaluations_by_student(db: Session, student_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Evaluation).filter(models.Evaluation.student_id == student_id).offset(skip).limit(limit).all()

def get_evaluation_by_application(db: Session, application_id: int):
    return db.query(models.Evaluation).filter(models.Evaluation.application_id == application_id).first()

def get_evaluations_by_internship(db: Session, internship_id: int):
    return db.query(models.Evaluation).filter(models.Evaluation.internship_id == internship_id).all()

def update_evaluation(db: Session, evaluation_id: int, evaluation_update: schemas.EvaluationUpdate):
    db_evaluation = db.query(models.Evaluation).filter(models.Evaluation.id == evaluation_id).first()
    if not db_evaluation:
        return None
    
    update_data = evaluation_update.dict(exclude_unset=True)
    
    # Recalculate overall score if any scores are updated
    if any(key in update_data for key in ['technical_competence', 'task_completion', 'communication_skills', 'professionalism', 'initiative']):
        scores = [
            update_data.get('technical_competence', db_evaluation.technical_competence),
            update_data.get('task_completion', db_evaluation.task_completion),
            update_data.get('communication_skills', db_evaluation.communication_skills),
            update_data.get('professionalism', db_evaluation.professionalism),
            update_data.get('initiative', db_evaluation.initiative)
        ]
        update_data['overall_score'] = sum(scores) / len(scores)
    
    for field, value in update_data.items():
        setattr(db_evaluation, field, value)
    
    db.commit()
    db.refresh(db_evaluation)
    return db_evaluation

def delete_evaluation(db: Session, evaluation_id: int):
    db_evaluation = db.query(models.Evaluation).filter(models.Evaluation.id == evaluation_id).first()
    if db_evaluation:
        db.delete(db_evaluation)
        db.commit()
    return db_evaluation

# Combined queries for templates
def get_mentor_feedbacks_with_relations(db: Session, user_id: int, user_role: str):
    query = db.query(models.MentorFeedback)
    
    if user_role == "mentor":
        query = query.filter(models.MentorFeedback.mentor_id == user_id)
    elif user_role == "student":
        query = query.filter(models.MentorFeedback.student_id == user_id)
    
    return query.all()

def get_evaluations_with_relations(db: Session, user_id: int, user_role: str):
    query = db.query(models.Evaluation)
    
    if user_role == "admin":
        query = query.filter(models.Evaluation.admin_id == user_id)
    elif user_role == "student":
        query = query.filter(models.Evaluation.student_id == user_id)
    
    return query.all()

# Get applications that need feedback (for mentors)
def get_applications_needing_feedback(db: Session, mentor_id: int):
    # Get internships created by this mentor
    mentor_internships = db.query(models.Internship).filter(
        models.Internship.created_by == mentor_id
    ).all()
    
    internship_ids = [internship.id for internship in mentor_internships]
    
    # Get approved applications for these internships that don't have feedback yet
    applications = db.query(models.InternshipApplication).filter(
        models.InternshipApplication.internship_id.in_(internship_ids),
        models.InternshipApplication.status == models.ApplicationStatus.APPROVED
    ).all()
    
    # Filter out applications that already have feedback
    applications_needing_feedback = []
    for application in applications:
        existing_feedback = get_mentor_feedback_by_application(db, application.id)
        if not existing_feedback:
            applications_needing_feedback.append(application)
    
    return applications_needing_feedback

# Get applications that need evaluation (for admins)
def get_applications_needing_evaluation(db: Session):
    # Get approved applications that don't have evaluations yet
    applications = db.query(models.InternshipApplication).filter(
        models.InternshipApplication.status == models.ApplicationStatus.APPROVED
    ).all()
    
    # Filter out applications that already have evaluations
    applications_needing_evaluation = []
    for application in applications:
        existing_evaluation = get_evaluation_by_application(db, application.id)
        if not existing_evaluation:
            applications_needing_evaluation.append(application)
    
    return applications_needing_evaluation

# Statistics and Analytics
def get_feedback_stats_by_mentor(db: Session, mentor_id: int):
    feedbacks = get_mentor_feedbacks_by_mentor(db, mentor_id)
    
    if not feedbacks:
        return {
            "total_feedbacks": 0,
            "average_rating": 0,
            "total_students": 0
        }
    
    total_feedbacks = len(feedbacks)
    valid_ratings = [f.overall_rating for f in feedbacks if f.overall_rating is not None]
    average_rating = sum(valid_ratings) / len(valid_ratings) if valid_ratings else 0
    unique_students = len(set(f.student_id for f in feedbacks))
    
    return {
        "total_feedbacks": total_feedbacks,
        "average_rating": round(average_rating, 2),
        "total_students": unique_students
    }

def get_evaluation_stats_by_admin(db: Session, admin_id: int):
    evaluations = get_evaluations_by_admin(db, admin_id)
    
    if not evaluations:
        return {
            "total_evaluations": 0,
            "average_score": 0,
            "total_students": 0
        }
    
    total_evaluations = len(evaluations)
    average_score = sum(e.overall_score for e in evaluations) / total_evaluations
    unique_students = len(set(e.student_id for e in evaluations))
    
    return {
        "total_evaluations": total_evaluations,
        "average_score": round(average_score, 2),
        "total_students": unique_students
    }

def get_student_feedback_stats(db: Session, student_id: int):
    feedbacks = get_mentor_feedbacks_by_student(db, student_id)
    evaluations = get_evaluations_by_student(db, student_id)
    
    feedback_stats = {
        "total_feedbacks": len(feedbacks),
        "average_feedback_rating": 0,
        "total_evaluations": len(evaluations),
        "average_evaluation_score": 0
    }
    
    if feedbacks:
        valid_ratings = [f.overall_rating for f in feedbacks if f.overall_rating is not None]
        if valid_ratings:
            feedback_stats["average_feedback_rating"] = round(sum(valid_ratings) / len(valid_ratings), 2)
    
    if evaluations:
        feedback_stats["average_evaluation_score"] = round(sum(e.overall_score for e in evaluations) / len(evaluations), 2)
    
    return feedback_stats

# Bulk Operations
def bulk_update_feedback_status(db: Session, feedback_ids: List[int], status: schemas.FeedbackStatus):
    feedbacks = db.query(models.MentorFeedback).filter(models.MentorFeedback.id.in_(feedback_ids)).all()
    
    for feedback in feedbacks:
        feedback.status = status
    
    db.commit()
    return feedbacks

def bulk_update_evaluation_status(db: Session, evaluation_ids: List[int], status: schemas.EvaluationStatus):
    evaluations = db.query(models.Evaluation).filter(models.Evaluation.id.in_(evaluation_ids)).all()
    
    for evaluation in evaluations:
        evaluation.status = status
    
    db.commit()
    return evaluations

# Search and Filter Operations
def search_mentor_feedbacks(db: Session, search_term: str, mentor_id: Optional[int] = None, student_id: Optional[int] = None):
    query = db.query(models.MentorFeedback)
    
    if mentor_id:
        query = query.filter(models.MentorFeedback.mentor_id == mentor_id)
    
    if student_id:
        query = query.filter(models.MentorFeedback.student_id == student_id)
    
    # Search in feedback comments
    if search_term:
        query = query.filter(
            models.MentorFeedback.overall_feedback.ilike(f"%{search_term}%") |
            models.MentorFeedback.technical_skills.ilike(f"%{search_term}%") |
            models.MentorFeedback.communication_skills.ilike(f"%{search_term}%")
        )
    
    return query.all()

def search_evaluations(db: Session, search_term: str, admin_id: Optional[int] = None, student_id: Optional[int] = None):
    query = db.query(models.Evaluation)
    
    if admin_id:
        query = query.filter(models.Evaluation.admin_id == admin_id)
    
    if student_id:
        query = query.filter(models.Evaluation.student_id == student_id)
    
    # Search in evaluation comments
    if search_term:
        query = query.filter(
            models.Evaluation.final_comments.ilike(f"%{search_term}%") |
            models.Evaluation.strengths.ilike(f"%{search_term}%") |
            models.Evaluation.areas_for_improvement.ilike(f"%{search_term}%")
        )
    
    return query.all()

# Get recent feedbacks and evaluations
def get_recent_mentor_feedbacks(db: Session, limit: int = 5):
    return db.query(models.MentorFeedback).order_by(models.MentorFeedback.feedback_date.desc()).limit(limit).all()

def get_recent_evaluations(db: Session, limit: int = 5):
    return db.query(models.Evaluation).order_by(models.Evaluation.evaluation_date.desc()).limit(limit).all()

# Check if user can provide feedback
def can_provide_feedback(db: Session, mentor_id: int, application_id: int):
    application = db.query(models.InternshipApplication).filter(
        models.InternshipApplication.id == application_id
    ).first()
    
    if not application:
        return False
    
    internship = db.query(models.Internship).filter(
        models.Internship.id == application.internship_id
    ).first()
    
    if not internship:
        return False
    
    # Check if mentor created this internship and application is approved
    return (internship.created_by == mentor_id and 
            application.status == models.ApplicationStatus.APPROVED and
            not get_mentor_feedback_by_application(db, application_id))

# Check if user can create evaluation
def can_create_evaluation(db: Session, admin_id: int, application_id: int):
    application = db.query(models.InternshipApplication).filter(
        models.InternshipApplication.id == application_id
    ).first()
    
    if not application:
        return False
    
    # Check if application is approved and no evaluation exists
    return (application.status == models.ApplicationStatus.APPROVED and
            not get_evaluation_by_application(db, application_id))