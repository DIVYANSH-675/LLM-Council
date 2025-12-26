"""
Safety Gate - Pre-processing safety check for queries
Blocks harmful queries before they reach the agents
"""

import re
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SafetyResult:
    """Result of safety check"""
    passed: bool
    reason: str
    matched_patterns: List[str]
    
    def __bool__(self) -> bool:
        """Allow using SafetyResult directly in if statements"""
        return self.passed


class SafetyGate:
    """
    Safety gate that checks queries before processing.
    Uses keyword matching, regex patterns, and length constraints.
    """
    
    def __init__(self, config_path: str = "config/safety.yaml"):
        """Initialize safety gate with configuration"""
        self.config_path = Path(config_path)
        self._load_config()
    
    def _load_config(self):
        """Load safety configuration from YAML"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Safety config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.blocked_keywords = config.get('blocked_keywords', [])
        self.blocked_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in config.get('blocked_patterns', [])
        ]
        self.allowlist_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in config.get('allowlist_patterns', [])
        ]
        
        constraints = config.get('constraints', {})
        self.max_query_length = constraints.get('max_query_length', 1000)
        self.min_query_length = constraints.get('min_query_length', 3)
    
    def check(self, query: str) -> SafetyResult:
        """
        Check if a query is safe to process.
        
        Returns:
            SafetyResult with passed=True if safe, False if blocked
        """
        # 1. Check for empty/None query
        if not query or not query.strip():
            return SafetyResult(
                passed=False,
                reason="Query is empty",
                matched_patterns=[]
            )
        
        query = query.strip()
        
        # 2. Check query length
        if len(query) < self.min_query_length:
            return SafetyResult(
                passed=False,
                reason=f"Query too short (min {self.min_query_length} chars)",
                matched_patterns=[]
            )
        
        if len(query) > self.max_query_length:
            return SafetyResult(
                passed=False,
                reason=f"Query too long (max {self.max_query_length} chars)",
                matched_patterns=[]
            )
        
        # 3. Check blocked keywords FIRST (security: blocklist before allowlist)
        query_lower = query.lower()
        for keyword in self.blocked_keywords:
            if keyword.lower() in query_lower:
                return SafetyResult(
                    passed=False,
                    reason=f"Blocked keyword detected: '{keyword}'",
                    matched_patterns=[keyword]
                )
        
        # 4. Check blocked regex patterns
        matched = []
        for pattern in self.blocked_patterns:
            if pattern.search(query):
                matched.append(pattern.pattern)
        
        if matched:
            return SafetyResult(
                passed=False,
                reason=f"Blocked pattern matched",
                matched_patterns=matched
            )
        
        # 5. Check allowlist AFTER blocklist (prevents bypass attacks)
        for pattern in self.allowlist_patterns:
            if pattern.search(query):
                return SafetyResult(
                    passed=True,
                    reason="Allowlisted query",
                    matched_patterns=[]
                )
        
        # All checks passed
        return SafetyResult(
            passed=True,
            reason="Query passed all safety checks",
            matched_patterns=[]
        )
    
    def is_safe(self, query: str) -> bool:
        """Simple boolean check for safety"""
        return self.check(query).passed
    
    def get_block_reason(self, query: str) -> Optional[str]:
        """Get the reason a query was blocked, or None if safe"""
        result = self.check(query)
        return None if result.passed else result.reason
    
    def redact(self, text: str) -> str:
        """
        Redact PII (Personally Identifiable Information) from text.
        Crucial for GDPR/Audit compliance.
        
        Redacts: Emails, Phone Numbers, Credit Card Numbers
        """
        if not text:
            return ""
        
        # 1. Redact Emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        text = re.sub(email_pattern, '[EMAIL_REDACTED]', text)
        
        # 2. Redact Phone Numbers (International format)
        phone_pattern = r'\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
        text = re.sub(phone_pattern, '[PHONE_REDACTED]', text)
        
        # 3. Redact Credit Cards (4x4 digit pattern)
        cc_pattern = r'\b(?:\d{4}[-\s]){3}\d{4}\b'
        text = re.sub(cc_pattern, '[CARD_REDACTED]', text)
        
        # 4. Redact SSN-like patterns (XXX-XX-XXXX)
        ssn_pattern = r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'
        text = re.sub(ssn_pattern, '[SSN_REDACTED]', text)
        
        return text
