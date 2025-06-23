#!/usr/bin/env python3
"""
Hidden Gems Models and Schemas
Clean, efficient data models for the Hidden Gem Discovery feature
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field
from enum import Enum


class ExclusivityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    ULTRA = "ULTRA"


# Flexible gem category - allowing any string for AI flexibility
# class GemCategory(str, Enum):
#     CULTURAL_CINEMA = "Cultural Cinema"
#     SECRET_DINING = "Secret Dining"
#     HIDDEN_ARTS = "Hidden Arts"
#     UNDERGROUND_MUSIC = "Underground Music"
#     EXCLUSIVE_WELLNESS = "Exclusive Wellness"
#     ROOFTOP_EXPERIENCES = "Rooftop Experiences"
#     HERITAGE_TOURS = "Heritage Tours"
#     ARTISAN_WORKSHOPS = "Artisan Workshops"
#     PRIVATE_GALLERIES = "Private Galleries"
#     POPUP_EXPERIENCES = "Pop-up Experiences"


class ScoringBreakdown(BaseModel):
    uniqueness: int = Field(..., ge=1, le=10, description="How unique the experience is")
    exclusivity: int = Field(..., ge=1, le=10, description="Level of exclusivity")
    cultural_significance: int = Field(..., ge=1, le=10, description="Cultural value")
    photo_opportunity: int = Field(..., ge=1, le=10, description="Instagram-worthiness")
    insider_knowledge: int = Field(..., ge=1, le=10, description="Local insider appeal")
    value_for_money: int = Field(..., ge=1, le=10, description="Value proposition")

    @property
    def total_score(self) -> int:
        """Calculate total score from all components"""
        return (
            self.uniqueness + self.exclusivity + self.cultural_significance +
            self.photo_opportunity + self.insider_knowledge + self.value_for_money
        )

    @property
    def weighted_score(self) -> float:
        """Calculate weighted score (out of 100)"""
        weights = {
            'uniqueness': 0.25,
            'exclusivity': 0.20,
            'cultural_significance': 0.15,
            'photo_opportunity': 0.15,
            'insider_knowledge': 0.15,
            'value_for_money': 0.10
        }
        
        return (
            self.uniqueness * weights['uniqueness'] * 10 +
            self.exclusivity * weights['exclusivity'] * 10 +
            self.cultural_significance * weights['cultural_significance'] * 10 +
            self.photo_opportunity * weights['photo_opportunity'] * 10 +
            self.insider_knowledge * weights['insider_knowledge'] * 10 +
            self.value_for_money * weights['value_for_money'] * 10
        )


class HiddenGem(BaseModel):
    """Core Hidden Gem model with all discovery details"""
    
    # Basic identification
    gem_id: str = Field(..., description="Unique identifier for the gem")
    event_id: str = Field(..., description="Associated event ID")
    
    # Gem content
    gem_title: str = Field(..., description="Captivating title for the gem")
    gem_tagline: str = Field(..., description="Intriguing one-liner")
    mystery_teaser: str = Field(..., description="Mysterious description before reveal")
    revealed_description: str = Field(..., description="Full description after reveal")
    why_hidden_gem: str = Field(..., description="Explanation of what makes it special")
    
    # Classification
    exclusivity_level: ExclusivityLevel
    gem_category: str = Field(..., description="Category name (flexible string for AI)")
    experience_level: str = Field(..., description="e.g., 'Intimate', 'Exclusive', 'Private'")
    best_for: List[str] = Field(default_factory=list, description="Target audience tags")
    
    # Scoring
    gem_score: int = Field(..., ge=0, le=100, description="Overall gem quality score")
    scoring_breakdown: ScoringBreakdown
    
    # Discovery elements
    discovery_hints: List[str] = Field(default_factory=list, description="Clues about the gem")
    insider_tips: List[str] = Field(default_factory=list, description="Pro tips for attendees")
    
    # Temporal data
    gem_date: datetime = Field(default_factory=datetime.now, description="When gem was created")
    reveal_time: str = Field(default="12:00 PM UAE", description="Daily reveal time")
    expires_at: Optional[datetime] = Field(None, description="When gem expires")
    
    # Analytics
    reveal_count: int = Field(default=0, description="Number of users who revealed")
    share_count: int = Field(default=0, description="Number of shares")
    feedback_score: Optional[float] = Field(None, description="User feedback average")
    
    # Event data (populated when needed for frontend)
    event: Optional[Dict[str, Any]] = Field(None, description="Full event data for navigation")
    
    # AI-generated event details for popup
    event_details: Optional[Dict[str, Any]] = Field(None, description="AI-generated event details for popup display")
    
    class Config:
        use_enum_values = True


class GemReveal(BaseModel):
    """User's interaction with a hidden gem"""
    
    user_id: str = Field(..., description="User who revealed the gem")
    gem_id: str = Field(..., description="Gem that was revealed")
    revealed_at: datetime = Field(default_factory=datetime.now)
    feedback_score: Optional[int] = Field(None, ge=1, le=5, description="User rating")
    shared: bool = Field(default=False, description="Whether user shared the gem")
    attended: Optional[bool] = Field(None, description="Whether user attended the event")


class UserGemStreak(BaseModel):
    """User's hidden gem discovery streak and achievements"""
    
    user_id: str = Field(..., description="User identifier")
    current_streak: int = Field(default=0, description="Current consecutive days")
    longest_streak: int = Field(default=0, description="All-time longest streak")
    total_gems_discovered: int = Field(default=0, description="Total gems revealed")
    last_discovery_date: Optional[date] = Field(None, description="Last discovery date")
    
    # Achievements
    achievements: List[str] = Field(default_factory=list, description="Earned badges")
    streak_milestones: List[Dict[str, Any]] = Field(default_factory=list, description="Streak achievements")
    
    def update_streak(self, discovery_date: date) -> Dict[str, Any]:
        """Update streak based on new discovery"""
        today = discovery_date
        yesterday = today - timedelta(days=1)
        
        result = {
            "streak_maintained": False,
            "streak_broken": False,
            "new_achievement": None,
            "previous_streak": self.current_streak
        }
        
        if self.last_discovery_date == yesterday:
            # Streak continues
            self.current_streak += 1
            result["streak_maintained"] = True
        elif self.last_discovery_date == today:
            # Same day discovery, no change
            return result
        else:
            # Streak broken or first discovery
            if self.current_streak > 0:
                result["streak_broken"] = True
            self.current_streak = 1
        
        # Update records
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
        
        self.total_gems_discovered += 1
        self.last_discovery_date = today
        
        # Check for achievements
        achievement = self._check_achievements()
        if achievement:
            result["new_achievement"] = achievement
        
        return result
    
    def _check_achievements(self) -> Optional[str]:
        """Check if user earned new achievements"""
        achievements_map = {
            1: "First Discovery",
            3: "Gem Seeker",
            7: "Weekly Explorer", 
            14: "Fortnight Hunter",
            30: "Monthly Master",
            50: "Gem Collector",
            100: "Hidden Gem Legend"
        }
        
        # Check streak achievements
        if self.current_streak in achievements_map:
            achievement = f"{achievements_map[self.current_streak]} ({self.current_streak} days)"
            if achievement not in self.achievements:
                self.achievements.append(achievement)
                return achievement
        
        # Check total discoveries
        total_achievements = {
            10: "Novice Explorer",
            25: "Experienced Seeker", 
            50: "Gem Specialist",
            100: "Discovery Master"
        }
        
        if self.total_gems_discovered in total_achievements:
            achievement = total_achievements[self.total_gems_discovered]
            if achievement not in self.achievements:
                self.achievements.append(achievement)
                return achievement
        
        return None


class DailyGemAnalytics(BaseModel):
    """Daily analytics for hidden gems"""
    
    date: date
    gem_id: str
    total_views: int = Field(default=0, description="Homepage views")
    total_reveals: int = Field(default=0, description="Users who clicked reveal")
    total_shares: int = Field(default=0, description="Social shares")
    unique_users: int = Field(default=0, description="Unique users who saw gem")
    
    reveal_rate: float = Field(default=0.0, description="Percentage who revealed")
    share_rate: float = Field(default=0.0, description="Percentage who shared")
    average_feedback: Optional[float] = Field(None, description="Average user rating")
    
    peak_activity_hour: Optional[int] = Field(None, description="Hour with most activity")
    
    def calculate_rates(self):
        """Calculate engagement rates"""
        if self.total_views > 0:
            self.reveal_rate = (self.total_reveals / self.total_views) * 100
        
        if self.total_reveals > 0:
            self.share_rate = (self.total_shares / self.total_reveals) * 100


# Request/Response Models for API
class GemRevealRequest(BaseModel):
    user_id: str
    feedback_score: Optional[int] = Field(None, ge=1, le=5)


class GemRevealResponse(BaseModel):
    success: bool
    gem: HiddenGem
    streak_info: Dict[str, Any]
    achievement_unlocked: Optional[str] = None


class UserStreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    total_discoveries: int
    achievements: List[str]
    next_milestone: Optional[Dict[str, Any]] = None


class DailyGemResponse(BaseModel):
    gem: HiddenGem
    user_revealed: bool = False
    user_streak: Optional[int] = None
    reveal_deadline: datetime