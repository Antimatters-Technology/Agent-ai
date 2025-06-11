import pandas as pd
import json
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class UniversityMatcher:
    def __init__(self):
        self.universities_df = None
        self.load_data()
    
    def load_data(self):
        """Load university data from CSV/JSON"""
        try:
            # Mock data - replace with actual CSV loading
            university_data = [
                {
                    "name": "University of Toronto",
                    "location": "Toronto, ON",
                    "programs": ["Computer Science", "Engineering", "Business"],
                    "tuition_intl": 58160,
                    "ranking": 34,
                    "requirements": {
                        "gpa": 3.7,
                        "ielts": 6.5,
                        "toefl": 100
                    }
                },
                {
                    "name": "University of British Columbia",
                    "location": "Vancouver, BC", 
                    "programs": ["Computer Science", "Medicine", "Arts"],
                    "tuition_intl": 52000,
                    "ranking": 47,
                    "requirements": {
                        "gpa": 3.5,
                        "ielts": 6.5,
                        "toefl": 90
                    }
                }
            ]
            
            self.universities_df = pd.DataFrame(university_data)
            logger.info(f"Loaded {len(self.universities_df)} universities")
            
        except Exception as e:
            logger.error(f"Failed to load university data: {str(e)}")
    
    def match_universities(self, student_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Match universities based on student profile"""
        if self.universities_df is None:
            return []
        
        gpa = student_profile.get("gpa", 0)
        ielts = student_profile.get("ielts", 0)
        budget = student_profile.get("budget", 0)
        
        # Filter universities
        matches = []
        for _, uni in self.universities_df.iterrows():
            score = self._calculate_match_score(uni, student_profile)
            if score > 0.6:  # 60% match threshold
                matches.append({
                    "university": uni.to_dict(),
                    "match_score": score,
                    "reasons": self._get_match_reasons(uni, student_profile)
                })
        
        return sorted(matches, key=lambda x: x["match_score"], reverse=True)
    
    def _calculate_match_score(self, university: pd.Series, profile: Dict) -> float:
        """Calculate match score between university and student"""
        score = 0.0
        
        # GPA match
        if profile.get("gpa", 0) >= university["requirements"]["gpa"]:
            score += 0.3
        
        # IELTS match
        if profile.get("ielts", 0) >= university["requirements"]["ielts"]:
            score += 0.3
        
        # Budget match
        if profile.get("budget", 0) >= university["tuition_intl"]:
            score += 0.4
        
        return min(score, 1.0)
    
    def _get_match_reasons(self, university: pd.Series, profile: Dict) -> List[str]:
        """Get reasons for the match"""
        reasons = []
        
        if profile.get("gpa", 0) >= university["requirements"]["gpa"]:
            reasons.append("GPA requirement met")
        
        if profile.get("ielts", 0) >= university["requirements"]["ielts"]:
            reasons.append("IELTS requirement met")
        
        return reasons