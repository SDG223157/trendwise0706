from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import (Column, Integer, String, Float, DateTime, 
                      Text, ForeignKey, Enum, UniqueConstraint, Boolean, Index)
from sqlalchemy.orm import relationship
import json

class NewsArticle(db.Model):
   __tablename__ = 'news_articles'

   id = db.Column(db.Integer, primary_key=True)
   external_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
   title = db.Column(db.String(255), nullable=False)
   content = db.Column(db.Text)
   url = db.Column(db.String(512))
   published_at = db.Column(db.DateTime, index=True)
   source = db.Column(db.String(100), index=True)
   sentiment_label = db.Column(db.String(20), index=True)
   sentiment_score = db.Column(db.Float, index=True)
   sentiment_explanation = db.Column(db.Text)
   brief_summary = db.Column(db.Text)
   key_points = db.Column(db.Text)
   market_impact_summary = db.Column(db.Text)
   ai_summary = db.Column(db.Text)
   ai_insights = db.Column(db.Text)
   ai_sentiment_rating = db.Column(db.Integer, index=True)
   created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
   
   symbols = relationship('ArticleSymbol', back_populates='article', cascade='all, delete-orphan')
   metrics = relationship('ArticleMetric', back_populates='article', cascade='all, delete-orphan')

   __table_args__ = (
       Index('idx_published_sentiment', 'published_at', 'ai_sentiment_rating'),
       Index('idx_published_created', 'published_at', 'created_at'),
       Index('idx_sentiment_published', 'sentiment_score', 'published_at'),
       Index('idx_ai_sentiment_published', 'ai_sentiment_rating', 'published_at'),
       Index('idx_source_published', 'source', 'published_at'),
       Index('idx_sentiment_label_published', 'sentiment_label', 'published_at'),
   )

   def to_dict(self):
       return {
           'id': self.id,
           'external_id': self.external_id,
           'title': self.title,
           'content': self.content,
           'url': self.url,
           'published_at': self.published_at.isoformat() if self.published_at else None,
           'source': self.source,
           'sentiment': {
               'label': self.sentiment_label,
               'score': self.sentiment_score,
               'explanation': self.sentiment_explanation
           },
           'summary': {
               'brief': self.brief_summary,
               'key_points': self.key_points,
               'market_impact': self.market_impact_summary,
               'ai_summary': self.ai_summary,
               'ai_insights': self.ai_insights,
               'ai_sentiment_rating': self.ai_sentiment_rating
           },
           'symbols': [symbol.to_dict() for symbol in self.symbols],
           'metrics': [metric.to_dict() for metric in self.metrics]
       }

class NewsSearchIndex(db.Model):
   """
   Optimized standalone search table for news articles with AI content.
   Contains all fields needed for AI-enhanced search without requiring joins.
   """
   __tablename__ = 'news_search_index'

   id = db.Column(db.Integer, primary_key=True)
   article_id = db.Column(db.Integer, db.ForeignKey('news_articles.id', ondelete='SET NULL'), nullable=True, index=True)
   external_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
   title = db.Column(db.String(255), nullable=False, index=True)
   url = db.Column(db.String(512))
   published_at = db.Column(db.DateTime, nullable=False, index=True)
   source = db.Column(db.String(100), nullable=False, index=True)
   ai_sentiment_rating = db.Column(db.Integer, index=True)
   symbols_json = db.Column(db.Text)  # JSON string of symbols for faster search
   # AI content fields for search
   ai_summary = db.Column(db.Text, index=True)  # AI-generated summary for search
   ai_insights = db.Column(db.Text, index=True)  # AI-generated insights for search
   created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
   updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
   
   # Relationship to original article (for buffer operations)
   article = db.relationship('NewsArticle', backref='search_index')

   __table_args__ = (
       # Composite indexes for common search patterns
       Index('idx_search_published_sentiment', 'published_at', 'ai_sentiment_rating'),
       Index('idx_search_source_published', 'source', 'published_at'),
       Index('idx_search_external_published', 'external_id', 'published_at'),
       # AI content search indexes
       Index('idx_search_ai_summary', 'ai_summary'),
       Index('idx_search_ai_insights', 'ai_insights'),
       Index('idx_search_ai_content', 'ai_summary', 'ai_insights'),
       Index('idx_search_title', 'title'),
       # Date-based indexes for cleanup
       Index('idx_search_created_updated', 'created_at', 'updated_at'),
   )

   def to_dict(self):
       """Convert to dictionary format with AI content from search index"""
       import json
       symbols = []
       if self.symbols_json:
           try:
               symbols = json.loads(self.symbols_json)
           except:
               symbols = []
       
       return {
           'id': self.article_id or self.id,  # Use original article ID or search index ID for compatibility
           'external_id': self.external_id,
           'title': self.title,
           'content': self.ai_summary,  # Use AI summary as primary content
           'url': self.url,
           'published_at': self.published_at.isoformat() if self.published_at else None,
           'source': self.source,
           'sentiment': {
               'label': None,  # Not stored in search index
               'score': None,  # Not stored in search index
               'explanation': None
           },
           'summary': {
               'brief': None,  # Not stored in search index
               'key_points': None,
               'market_impact': None,
               'ai_summary': self.ai_summary,
               'ai_insights': self.ai_insights,
               'ai_sentiment_rating': self.ai_sentiment_rating
           },
           'symbols': [{'symbol': symbol} for symbol in symbols],
           'metrics': []  # Not stored in search index
       }

   def update_from_article(self, article):
       """Update search index from a NewsArticle instance with AI content"""
       import json
       self.article_id = article.id
       self.external_id = article.external_id
       self.title = article.title
       self.url = article.url
       self.published_at = article.published_at
       self.source = article.source
       self.ai_sentiment_rating = article.ai_sentiment_rating
       
       # Store AI content for search
       self.ai_summary = article.ai_summary
       self.ai_insights = article.ai_insights
       
       # Store symbols as JSON for faster search
       symbols = [symbol.symbol for symbol in article.symbols]
       self.symbols_json = json.dumps(symbols)
       self.updated_at = datetime.utcnow()

   @classmethod
   def create_from_article(cls, article):
       """Create search index entry from a NewsArticle instance"""
       search_index = cls()
       search_index.update_from_article(article)
       return search_index

class ArticleSymbol(db.Model):
   __tablename__ = 'article_symbols'
   
   article_id = db.Column(db.Integer, db.ForeignKey('news_articles.id', ondelete='CASCADE'), primary_key=True)
   symbol = db.Column(db.String(20), primary_key=True, index=True)

   article = db.relationship('NewsArticle', back_populates='symbols')

   __table_args__ = (
       db.UniqueConstraint('article_id', 'symbol'),
       Index('idx_symbol_article', 'symbol', 'article_id'),
   )

   def to_dict(self):
       return {
           'symbol': self.symbol
       }

class ArticleMetric(db.Model):
   __tablename__ = 'article_metrics'

   article_id = db.Column(db.Integer, db.ForeignKey('news_articles.id', ondelete='CASCADE'), primary_key=True)
   metric_type = db.Column(db.Enum('percentage', 'currency', name='metric_type_enum'), primary_key=True)
   metric_value = db.Column(db.Float)
   metric_context = db.Column(db.Text)

   article = db.relationship('NewsArticle', back_populates='metrics')

   def to_dict(self):
       return {
           'type': self.metric_type,
           'value': self.metric_value,
           'context': self.metric_context
       }

class User(UserMixin, db.Model):
   __tablename__ = 'users'
   
   id = db.Column(db.Integer, primary_key=True)
   email = db.Column(db.String(120), unique=True, nullable=False)
   username = db.Column(db.String(64), unique=True, nullable=False)
   password_hash = db.Column(db.String(255), nullable=False)
   first_name = db.Column(db.String(64))
   last_name = db.Column(db.String(64))
   created_at = db.Column(db.DateTime, default=datetime.utcnow)
   last_login = db.Column(db.DateTime)
   is_active = db.Column(db.Boolean, default=True)
   is_admin = db.Column(db.Boolean, default=False)
   role = db.Column(db.String(20), default='user')
   is_google_user = db.Column(db.Boolean, default=False)
   
   def set_password(self, password):
       self.password_hash = generate_password_hash(password)
       
   def check_password(self, password):
       return check_password_hash(self.password_hash, password)
   
   def update_last_login(self):
       self.last_login = datetime.utcnow()
       db.session.commit()
       
   @property
   def is_administrator(self):
       return self.is_admin or self.role == 'admin'
       
   def to_dict(self):
       return {
           'id': self.id,
           'email': self.email,
           'username': self.username,
           'first_name': self.first_name,
           'last_name': self.last_name,
           'created_at': self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
           'last_login': self.last_login.strftime("%Y-%m-%d %H:%M:%S") if self.last_login else None,
           'is_active': self.is_active,
           'is_admin': self.is_admin,
           'role': self.role,
           'is_google_user': self.is_google_user
       }

   def __repr__(self):
       return f'<User {self.username}>'

class UserActivity(db.Model):
    __tablename__ = 'user_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    activity_type = db.Column(db.String(50))  # login, logout, search, fetch_news, etc.
    description = db.Column(db.String(255))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('activities', lazy='dynamic'))
    
    def __repr__(self):
        return f'<UserActivity {self.activity_type}: {self.user.username if self.user else "Unknown"} at {self.timestamp}>'

class NewsKeyword(db.Model):
    """
    Extracted keywords and concepts from news articles for intelligent search suggestions.
    This table stores AI-extracted keywords with relevance scoring and semantic relationships.
    """
    __tablename__ = 'news_keywords'
    
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(100), nullable=False, index=True)
    normalized_keyword = db.Column(db.String(100), nullable=False, index=True)  # Lowercase, stemmed
    category = db.Column(db.String(50), nullable=False, index=True)  # 'company', 'technology', 'financial', 'industry', 'concept'
    relevance_score = db.Column(db.Float, default=0.0, index=True)  # AI-calculated relevance
    frequency = db.Column(db.Integer, default=1, index=True)  # How often this keyword appears
    sentiment_association = db.Column(db.Float, default=0.0)  # Average sentiment when this keyword appears
    first_seen = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    article_keywords = relationship('ArticleKeyword', back_populates='keyword_ref', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.UniqueConstraint('normalized_keyword', 'category'),
        Index('idx_keyword_relevance', 'keyword', 'relevance_score'),
        Index('idx_keyword_frequency', 'keyword', 'frequency'),
        Index('idx_keyword_category_relevance', 'category', 'relevance_score'),
        Index('idx_keyword_search', 'normalized_keyword', 'category', 'frequency'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'keyword': self.keyword,
            'category': self.category,
            'relevance_score': self.relevance_score,
            'frequency': self.frequency,
            'sentiment_association': self.sentiment_association,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }


class ArticleKeyword(db.Model):
    """
    Junction table linking articles to their extracted keywords with context-specific scoring.
    """
    __tablename__ = 'article_keywords'
    
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('news_articles.id', ondelete='CASCADE'), nullable=False, index=True)
    keyword_id = db.Column(db.Integer, db.ForeignKey('news_keywords.id', ondelete='CASCADE'), nullable=False, index=True)
    relevance_in_article = db.Column(db.Float, default=0.0)  # How relevant this keyword is to this specific article
    extraction_source = db.Column(db.String(20), default='ai_summary')  # 'title', 'ai_summary', 'ai_insights'
    position_weight = db.Column(db.Float, default=1.0)  # Higher weight for keywords appearing early/prominently
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    article = relationship('NewsArticle', backref='article_keywords')
    keyword_ref = relationship('NewsKeyword', back_populates='article_keywords')
    
    __table_args__ = (
        db.UniqueConstraint('article_id', 'keyword_id'),
        Index('idx_article_keyword_relevance', 'article_id', 'relevance_in_article'),
        Index('idx_keyword_article_relevance', 'keyword_id', 'relevance_in_article'),
    )


class KeywordSimilarity(db.Model):
    """
    Stores semantic similarity relationships between keywords for intelligent suggestions.
    """
    __tablename__ = 'keyword_similarities'
    
    id = db.Column(db.Integer, primary_key=True)
    keyword1_id = db.Column(db.Integer, db.ForeignKey('news_keywords.id', ondelete='CASCADE'), nullable=False, index=True)
    keyword2_id = db.Column(db.Integer, db.ForeignKey('news_keywords.id', ondelete='CASCADE'), nullable=False, index=True)
    similarity_score = db.Column(db.Float, nullable=False, index=True)  # 0.0 to 1.0
    relationship_type = db.Column(db.String(50), default='semantic')  # 'semantic', 'co-occurrence', 'synonym'
    confidence = db.Column(db.Float, default=0.0)  # Confidence in the similarity
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    keyword1 = relationship('NewsKeyword', foreign_keys=[keyword1_id])
    keyword2 = relationship('NewsKeyword', foreign_keys=[keyword2_id])
    
    __table_args__ = (
        db.UniqueConstraint('keyword1_id', 'keyword2_id'),
        Index('idx_similarity_score', 'similarity_score'),
        Index('idx_keyword_similarity', 'keyword1_id', 'similarity_score'),
    )


class SearchAnalytics(db.Model):
    """
    Track user search patterns to improve keyword suggestions and search experience.
    """
    __tablename__ = 'search_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)  # Can be null for anonymous
    session_id = db.Column(db.String(100), nullable=False, index=True)  # Browser session
    search_query = db.Column(db.String(500), nullable=False, index=True)
    search_type = db.Column(db.String(20), nullable=False)  # 'symbol', 'keyword', 'mixed'
    results_count = db.Column(db.Integer, default=0)
    clicked_suggestions = db.Column(db.Text)  # JSON array of suggestions clicked
    selected_keywords = db.Column(db.Text)  # JSON array of final keywords used
    search_duration_ms = db.Column(db.Integer, default=0)  # Time to complete search
    result_clicked = db.Column(db.Boolean, default=False)  # Whether user clicked any results
    search_satisfied = db.Column(db.Boolean, default=None)  # Whether search was successful (inferred)
    ip_address = db.Column(db.String(45), index=True)
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship('User', backref='search_analytics')
    
    __table_args__ = (
        Index('idx_search_analytics_query', 'search_query'),
        Index('idx_search_analytics_time', 'created_at'),
        Index('idx_search_analytics_session', 'session_id', 'created_at'),
        Index('idx_search_analytics_user_time', 'user_id', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'search_query': self.search_query,
            'search_type': self.search_type,
            'results_count': self.results_count,
            'clicked_suggestions': json.loads(self.clicked_suggestions) if self.clicked_suggestions else [],
            'selected_keywords': json.loads(self.selected_keywords) if self.selected_keywords else [],
            'search_duration_ms': self.search_duration_ms,
            'result_clicked': self.result_clicked,
            'search_satisfied': self.search_satisfied,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }