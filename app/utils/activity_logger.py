from flask import request, g, current_app

def log_user_activity(user_id, activity_type, description=None):
    """
    Log user activity to the database
    
    Args:
        user_id (int): ID of the user performing the activity
        activity_type (str): Type of activity (e.g., login, logout, search)
        description (str, optional): Additional details about the activity
    """
    # Only log login and logout activities
    if activity_type not in ['login', 'logout']:
        return
        
    # Import inside function to avoid circular imports
    from app import db
    from app.models import UserActivity
    
    try:
        user_activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None
        )
        db.session.add(user_activity)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error logging user activity: {str(e)}")