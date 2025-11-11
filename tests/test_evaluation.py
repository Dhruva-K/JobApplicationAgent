"""
Evaluation metrics for the Job Application Agent system.
"""

import pytest
from typing import List, Dict, Any
from unittest.mock import Mock


class EvaluationMetrics:
    """Evaluation metrics for job matching and document generation."""
    
    @staticmethod
    def calculate_precision(true_positives: int, false_positives: int) -> float:
        """Calculate precision metric.
        
        Args:
            true_positives: Number of true positives
            false_positives: Number of false positives
            
        Returns:
            Precision score (0.0 to 1.0)
        """
        total = true_positives + false_positives
        if total == 0:
            return 0.0
        return true_positives / total
    
    @staticmethod
    def calculate_recall(true_positives: int, false_negatives: int) -> float:
        """Calculate recall metric.
        
        Args:
            true_positives: Number of true positives
            false_negatives: Number of false negatives
            
        Returns:
            Recall score (0.0 to 1.0)
        """
        total = true_positives + false_negatives
        if total == 0:
            return 0.0
        return true_positives / total
    
    @staticmethod
    def calculate_f1_score(precision: float, recall: float) -> float:
        """Calculate F1 score.
        
        Args:
            precision: Precision score
            recall: Recall score
            
        Returns:
            F1 score (0.0 to 1.0)
        """
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)
    
    @staticmethod
    def evaluate_matching(
        predicted_matches: List[Dict[str, Any]],
        ground_truth: List[str]
    ) -> Dict[str, float]:
        """Evaluate job matching performance.
        
        Args:
            predicted_matches: List of predicted job matches
            ground_truth: List of job IDs that should be matched
            
        Returns:
            Dictionary of evaluation metrics
        """
        predicted_ids = {match.get("job_id") for match in predicted_matches}
        ground_truth_set = set(ground_truth)
        
        true_positives = len(predicted_ids & ground_truth_set)
        false_positives = len(predicted_ids - ground_truth_set)
        false_negatives = len(ground_truth_set - predicted_ids)
        
        precision = EvaluationMetrics.calculate_precision(true_positives, false_positives)
        recall = EvaluationMetrics.calculate_recall(true_positives, false_negatives)
        f1 = EvaluationMetrics.calculate_f1_score(precision, recall)
        
        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives
        }
    
    @staticmethod
    def evaluate_document_quality(
        document: str,
        job_description: str,
        required_skills: List[str]
    ) -> Dict[str, Any]:
        """Evaluate document quality.
        
        Args:
            document: Generated document text
            job_description: Original job description
            required_skills: List of required skills
            
        Returns:
            Dictionary of quality metrics
        """
        document_lower = document.lower()
        job_lower = job_description.lower()
        
        # Skill coverage: how many required skills are mentioned
        skills_mentioned = sum(
            1 for skill in required_skills
            if skill.lower() in document_lower
        )
        skill_coverage = skills_mentioned / len(required_skills) if required_skills else 0.0
        
        # Relevance: keyword overlap
        job_words = set(job_lower.split())
        doc_words = set(document_lower.split())
        common_words = job_words & doc_words
        relevance = len(common_words) / len(job_words) if job_words else 0.0
        
        # Length check (not too short, not too long)
        word_count = len(document.split())
        length_score = 1.0 if 100 <= word_count <= 1000 else 0.5
        
        return {
            "skill_coverage": skill_coverage,
            "relevance": relevance,
            "length_score": length_score,
            "word_count": word_count
        }


def test_precision_calculation():
    """Test precision calculation."""
    precision = EvaluationMetrics.calculate_precision(8, 2)
    assert precision == 0.8


def test_recall_calculation():
    """Test recall calculation."""
    recall = EvaluationMetrics.calculate_recall(8, 2)
    assert recall == 0.8


def test_f1_score_calculation():
    """Test F1 score calculation."""
    f1 = EvaluationMetrics.calculate_f1_score(0.8, 0.8)
    assert f1 == 0.8


def test_matching_evaluation():
    """Test matching evaluation."""
    predicted = [
        {"job_id": "job1", "match_score": 0.9},
        {"job_id": "job2", "match_score": 0.8},
        {"job_id": "job3", "match_score": 0.7}
    ]
    ground_truth = ["job1", "job2", "job4"]
    
    metrics = EvaluationMetrics.evaluate_matching(predicted, ground_truth)
    
    assert metrics["precision"] > 0
    assert metrics["recall"] > 0
    assert metrics["f1_score"] > 0


def test_document_quality_evaluation():
    """Test document quality evaluation."""
    document = "I am a Python developer with experience in Django and PostgreSQL."
    job_description = "Looking for a Python developer with Django experience."
    required_skills = ["Python", "Django", "PostgreSQL"]
    
    metrics = EvaluationMetrics.evaluate_document_quality(
        document, job_description, required_skills
    )
    
    assert metrics["skill_coverage"] > 0
    assert metrics["relevance"] > 0
    assert "word_count" in metrics

