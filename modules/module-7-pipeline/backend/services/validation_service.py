"""
Answer Validation Service.

Provides quality control for RAG responses:
1. Pre-generation: Filter irrelevant chunks (entity conflicts, low relevance)
2. Post-generation: Validate answer quality (completeness, grounding, accuracy)

This is a critical component for production RAG systems to ensure
users receive accurate, relevant answers.
"""

import logging
import json
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

from openai import AzureOpenAI

from config.settings import get_settings

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationIssue:
    """A single validation issue found."""
    severity: ValidationSeverity
    issue_type: str
    description: str
    chunk_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ChunkValidationResult:
    """Result of validating a single chunk."""
    chunk_id: str
    is_relevant: bool
    relevance_score: float  # 0-1
    entity_conflict: bool
    conflict_details: Optional[str] = None
    reasoning: str = ""


@dataclass
class AnswerValidationResult:
    """Result of validating the generated answer."""
    overall_quality: float  # 0-100
    is_grounded: bool
    completeness_score: float  # 0-100
    aspects_answered: List[str] = field(default_factory=list)
    aspects_missing: List[str] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)
    confidence: str = "medium"  # low, medium, high
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Complete validation report for a RAG response."""
    # Chunk validation
    total_chunks_retrieved: int = 0
    chunks_kept: int = 0
    chunks_filtered: int = 0
    filtered_chunk_ids: List[str] = field(default_factory=list)
    filtered_reasons: List[Dict[str, str]] = field(default_factory=list)
    chunk_validations: List[ChunkValidationResult] = field(default_factory=list)
    
    # Answer validation
    answer_quality: Optional[AnswerValidationResult] = None
    
    # Overall
    overall_score: float = 0.0
    validation_passed: bool = True
    retry_suggested: bool = False
    retry_query: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class ValidationService:
    """
    Validates RAG retrieval and generation quality.
    
    Two-stage validation:
    1. Pre-generation: Filter chunks with entity conflicts or low relevance
    2. Post-generation: Validate answer completeness and grounding
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._openai_client = None
        logger.info("ValidationService initialized")
    
    @property
    def openai_client(self) -> AzureOpenAI:
        """Get OpenAI client."""
        if self._openai_client is None:
            self._openai_client = AzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version="2024-06-01"
            )
        return self._openai_client
    
    async def validate_chunks(
        self,
        query: str,
        chunks: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], ValidationReport]:
        """
        Validate retrieved chunks and filter out irrelevant ones.
        
        Checks:
        1. Entity conflicts (e.g., query asks about station 36, chunk is about station 37)
        2. Relevance to the query
        
        Returns:
            Tuple of (filtered_chunks, validation_report)
        """
        logger.info(f"Validating {len(chunks)} chunks for query: {query[:50]}...")
        
        report = ValidationReport(total_chunks_retrieved=len(chunks))
        
        if not chunks:
            return [], report
        
        # Extract query entities first
        query_entities = await self._extract_query_entities(query)
        logger.info(f"Query entities: {query_entities}")
        
        # Validate each chunk
        valid_chunks = []
        
        for chunk in chunks:
            validation = await self._validate_single_chunk(
                query=query,
                query_entities=query_entities,
                chunk=chunk
            )
            report.chunk_validations.append(validation)
            
            if validation.is_relevant and not validation.entity_conflict:
                valid_chunks.append(chunk)
            else:
                report.filtered_chunk_ids.append(validation.chunk_id)
                report.filtered_reasons.append({
                    "chunk_id": validation.chunk_id,
                    "reason": validation.conflict_details or "Low relevance",
                    "relevance_score": validation.relevance_score,
                    "entity_conflict": validation.entity_conflict
                })
        
        report.chunks_kept = len(valid_chunks)
        report.chunks_filtered = len(chunks) - len(valid_chunks)
        
        if report.chunks_filtered > 0:
            report.warnings.append(
                f"Filtered {report.chunks_filtered} chunks due to entity conflicts or low relevance"
            )
        
        logger.info(f"Chunk validation complete: {report.chunks_kept} kept, {report.chunks_filtered} filtered")
        
        return valid_chunks, report
    
    async def validate_answer(
        self,
        query: str,
        answer: str,
        chunks: List[Dict[str, Any]],
        report: ValidationReport
    ) -> ValidationReport:
        """
        Validate the generated answer for quality.
        
        Checks:
        1. Is the answer grounded in the chunks?
        2. Does it answer all aspects of the query?
        3. Are there any hallucinations or inaccuracies?
        
        Returns:
            Updated validation report with answer validation
        """
        logger.info("Validating generated answer...")
        
        # Prepare chunk summaries for validation
        chunk_summaries = "\n---\n".join([
            f"[Chunk {i+1}]: {c.get('content', '')[:300]}..."
            for i, c in enumerate(chunks[:10])
        ])
        
        response = self.openai_client.chat.completions.create(
            model=self.settings.azure_openai_deployment,
            messages=[
                {
                    "role": "system",
                    "content": """You are a RAG answer quality validator. Analyze if the answer is accurate and complete.

Return a JSON object:
{
    "overall_quality": <0-100>,
    "is_grounded": <true if answer is based on provided chunks>,
    "completeness_score": <0-100, how much of the query is answered>,
    "aspects_answered": ["list of query aspects that were answered"],
    "aspects_missing": ["list of query aspects NOT answered"],
    "issues": [
        {"severity": "warning|error", "type": "issue type", "description": "details"}
    ],
    "confidence": "low|medium|high",
    "recommendations": ["suggestions to improve the answer"]
}

Issue types: "hallucination", "incomplete", "entity_mismatch", "unsupported_claim", "missing_citation"

Be strict but fair. Only flag real issues."""
                },
                {
                    "role": "user",
                    "content": f"""Query: {query}

Generated Answer:
{answer}

Source Chunks:
{chunk_summaries}

Validate if the answer correctly addresses the query using the source chunks."""
                }
            ],
            temperature=0,
            max_tokens=1000
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            
            issues = [
                ValidationIssue(
                    severity=ValidationSeverity(issue.get("severity", "warning")),
                    issue_type=issue.get("type", "unknown"),
                    description=issue.get("description", "")
                )
                for issue in result.get("issues", [])
            ]
            
            report.answer_quality = AnswerValidationResult(
                overall_quality=result.get("overall_quality", 50),
                is_grounded=result.get("is_grounded", False),
                completeness_score=result.get("completeness_score", 50),
                aspects_answered=result.get("aspects_answered", []),
                aspects_missing=result.get("aspects_missing", []),
                issues=issues,
                confidence=result.get("confidence", "medium"),
                recommendations=result.get("recommendations", [])
            )
            
            # Calculate overall score
            report.overall_score = (
                report.answer_quality.overall_quality * 0.5 +
                report.answer_quality.completeness_score * 0.3 +
                (100 if report.answer_quality.is_grounded else 0) * 0.2
            )
            
            # Determine if retry is needed
            if report.overall_score < 50 or not report.answer_quality.is_grounded:
                report.validation_passed = False
                report.retry_suggested = True
                
                # Generate improved query for retry
                if report.answer_quality.aspects_missing:
                    report.retry_query = await self._generate_retry_query(
                        query, report.answer_quality.aspects_missing
                    )
                    report.warnings.append(
                        f"Low quality answer detected. Consider searching for: {report.retry_query}"
                    )
            
            # Add warnings based on issues
            for issue in issues:
                if issue.severity == ValidationSeverity.ERROR:
                    report.warnings.append(f"❌ {issue.issue_type}: {issue.description}")
                elif issue.severity == ValidationSeverity.WARNING:
                    report.warnings.append(f"⚠️ {issue.issue_type}: {issue.description}")
            
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse answer validation: {e}")
            report.answer_quality = AnswerValidationResult(
                overall_quality=50,
                is_grounded=True,
                completeness_score=50,
                confidence="low"
            )
            report.overall_score = 50
        
        logger.info(f"Answer validation complete: quality={report.overall_score:.1f}, passed={report.validation_passed}")
        
        return report
    
    async def _extract_query_entities(self, query: str) -> Dict[str, List[str]]:
        """
        Extract named entities from the query.
        
        Returns dict like:
        {
            "station": ["36"],
            "product": ["iPhone 15"],
            "person": ["John Smith"]
        }
        """
        response = self.openai_client.chat.completions.create(
            model=self.settings.azure_openai_deployment,
            messages=[
                {
                    "role": "system",
                    "content": """Extract specific identifiable entities from the query.

Look for:
- Numbers with context (station 36, chapter 5, version 2.0)
- Named items (product names, person names, place names)
- IDs (order #12345, ticket ABC-123)

Return JSON:
{
    "entity_type": ["value1", "value2"]
}

Examples:
- "תחנה 36" → {"station": ["36"]}
- "iPhone 15 Pro vs Samsung S24" → {"product": ["iPhone 15 Pro", "Samsung S24"]}
- "Chapter 5 of the manual" → {"chapter": ["5"]}

Return {} if no specific entities found.
Return ONLY the JSON."""
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            temperature=0,
            max_tokens=200
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    async def _validate_single_chunk(
        self,
        query: str,
        query_entities: Dict[str, List[str]],
        chunk: Dict[str, Any]
    ) -> ChunkValidationResult:
        """
        Validate a single chunk for relevance and entity conflicts.
        """
        chunk_id = chunk.get("id", "unknown")
        content = chunk.get("content", "")[:500]
        
        # If no specific entities in query, just check general relevance
        if not query_entities:
            return ChunkValidationResult(
                chunk_id=chunk_id,
                is_relevant=True,
                relevance_score=0.8,
                entity_conflict=False,
                reasoning="No specific entities to validate against"
            )
        
        # Check for entity conflicts
        response = self.openai_client.chat.completions.create(
            model=self.settings.azure_openai_deployment,
            messages=[
                {
                    "role": "system",
                    "content": """Determine if this chunk is relevant to the query or contains conflicting entity information.

CRITICAL: Check if the chunk mentions a DIFFERENT entity of the SAME TYPE as the query.

Examples of conflicts:
- Query about "station 36" but chunk is about "station 37" → CONFLICT
- Query about "iPhone 15" but chunk is about "iPhone 14" → CONFLICT
- Query about "Chapter 3" but chunk is about "Chapter 5" → CONFLICT

Return JSON:
{
    "is_relevant": <true/false>,
    "relevance_score": <0.0-1.0>,
    "entity_conflict": <true if chunk mentions DIFFERENT entity of same type>,
    "conflict_details": "explanation if conflict exists",
    "reasoning": "brief explanation"
}

Be STRICT about entity conflicts. Numbers matter!"""
                },
                {
                    "role": "user",
                    "content": f"""Query: {query}
Query entities: {json.dumps(query_entities, ensure_ascii=False)}

Chunk content:
{content}

Does this chunk have entity conflicts with the query?"""
                }
            ],
            temperature=0,
            max_tokens=300
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            return ChunkValidationResult(
                chunk_id=chunk_id,
                is_relevant=result.get("is_relevant", True),
                relevance_score=result.get("relevance_score", 0.5),
                entity_conflict=result.get("entity_conflict", False),
                conflict_details=result.get("conflict_details"),
                reasoning=result.get("reasoning", "")
            )
        except (json.JSONDecodeError, TypeError):
            # Default to keeping the chunk if validation fails
            return ChunkValidationResult(
                chunk_id=chunk_id,
                is_relevant=True,
                relevance_score=0.5,
                entity_conflict=False,
                reasoning="Validation failed, keeping chunk"
            )
    
    async def _generate_retry_query(
        self,
        original_query: str,
        missing_aspects: List[str]
    ) -> str:
        """Generate an improved query for retry."""
        response = self.openai_client.chat.completions.create(
            model=self.settings.azure_openai_deployment,
            messages=[
                {
                    "role": "system",
                    "content": """Generate an improved search query to find the missing information.

Combine the original query focus with the missing aspects.
Keep the same language as the original query.
Return ONLY the improved query, no explanation."""
                },
                {
                    "role": "user",
                    "content": f"""Original query: {original_query}
Missing aspects: {missing_aspects}

Generate improved query:"""
                }
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()
