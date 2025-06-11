import pandas as pd
import json
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class CSVProcessor:
    def __init__(self):
        pass
    
    def process_university_csv(self, csv_path: str) -> Dict[str, Any]:
        """Process university CSV and normalize data"""
        try:
            df = pd.read_csv(csv_path)
            
            # Clean and normalize data
            df.columns = df.columns.str.lower().str.replace(' ', '_')
            df = df.dropna(subset=['name', 'location'])
            
            # Convert to standardized format
            universities = []
            for _, row in df.iterrows():
                uni_data = {
                    "name": row.get("name", ""),
                    "location": row.get("location", ""),
                    "programs": self._parse_programs(row.get("programs", "")),
                    "tuition_intl": self._parse_tuition(row.get("tuition_international", 0)),
                    "ranking": int(row.get("ranking", 0)) if row.get("ranking") else None,
                    "requirements": self._parse_requirements(row)
                }
                universities.append(uni_data)
            
            return {
                "total_universities": len(universities),
                "universities": universities,
                "processed_at": pd.Timestamp.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"CSV processing failed: {str(e)}")
            return {"error": str(e)}
    
    def _parse_programs(self, programs_str: str) -> List[str]:
        """Parse programs string into list"""
        if pd.isna(programs_str):
            return []
        return [p.strip() for p in str(programs_str).split(',')]
    
    def _parse_tuition(self, tuition_str) -> int:
        """Parse tuition string to integer"""
        if pd.isna(tuition_str):
            return 0
        
        # Remove currency symbols and convert
        tuition_clean = str(tuition_str).replace('$', '').replace(',', '').replace('CAD', '').strip()
        try:
            return int(float(tuition_clean))
        except ValueError:
            return 0
    
    def _parse_requirements(self, row: pd.Series) -> Dict[str, float]:
        """Parse admission requirements"""
        return {
            "gpa": float(row.get("min_gpa", 0)) if row.get("min_gpa") else 0,
            "ielts": float(row.get("min_ielts", 0)) if row.get("min_ielts") else 0,
            "toefl": float(row.get("min_toefl", 0)) if row.get("min_toefl") else 0
        }