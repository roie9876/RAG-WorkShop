"""
Azure Content Understanding Client.
Based on Microsoft's sample: https://github.com/Azure-Samples/azure-ai-search-with-content-understanding-python
"""

import requests
import logging
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)


class AzureContentUnderstandingClient:
    """
    Client for Azure Content Understanding API.
    
    Supports:
    - Creating/deleting analyzers
    - Analyzing documents (returns markdown + structured content)
    - Polling for async operation results
    """
    
    def __init__(
        self,
        endpoint: str,
        api_version: str = "2025-11-01",
        subscription_key: Optional[str] = None,
        token_provider: Optional[Callable] = None,
        x_ms_useragent: str = "rag-workshop-pipeline",
    ):
        """
        Initialize the Content Understanding client.
        
        Args:
            endpoint: Azure AI Services endpoint
            api_version: API version to use
            subscription_key: Subscription key for authentication
            token_provider: Callable that returns bearer token (alternative to key)
            x_ms_useragent: User agent string for telemetry
        """
        if not subscription_key and not token_provider:
            raise ValueError("Either subscription_key or token_provider must be provided.")
        if not endpoint:
            raise ValueError("Endpoint must be provided.")
        
        # CRITICAL: Content Understanding uses .services.ai.azure.com NOT .cognitiveservices.azure.com
        endpoint = endpoint.rstrip("/")
        if ".cognitiveservices.azure.com" in endpoint:
            endpoint = endpoint.replace(".cognitiveservices.azure.com", ".services.ai.azure.com")
            logger.info(f"Converted endpoint to services.ai.azure.com format")
        
        self._endpoint = endpoint
        self._api_version = api_version
        self._subscription_key = subscription_key
        self._token_provider = token_provider
        self._x_ms_useragent = x_ms_useragent
        
        logger.info(f"ContentUnderstandingClient initialized for {self._endpoint}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for HTTP requests."""
        if self._subscription_key:
            headers = {"Ocp-Apim-Subscription-Key": self._subscription_key}
        else:
            token = self._token_provider()
            headers = {"Authorization": f"Bearer {token}"}
        
        headers["x-ms-useragent"] = self._x_ms_useragent
        return headers
    
    def _get_analyzer_url(self, analyzer_id: str) -> str:
        """Get URL for analyzer operations."""
        return f"{self._endpoint}/contentunderstanding/analyzers/{analyzer_id}?api-version={self._api_version}"
    
    def _get_analyze_url(self, analyzer_id: str) -> str:
        """Get URL for analyze operations (JSON body with URL)."""
        return f"{self._endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyze?api-version={self._api_version}"
    
    def _get_analyze_binary_url(self, analyzer_id: str) -> str:
        """Get URL for analyze binary operations (raw bytes body)."""
        return f"{self._endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyzeBinary?api-version={self._api_version}"
    
    def get_analyzer(self, analyzer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get analyzer details by ID.
        
        Returns None if analyzer doesn't exist.
        """
        try:
            response = requests.get(
                url=self._get_analyzer_url(analyzer_id),
                headers=self._get_headers(),
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.warning(f"Failed to get analyzer {analyzer_id}: {e}")
            return None
    
    def create_analyzer(
        self,
        analyzer_id: str,
        analyzer_template: Optional[Dict] = None,
        analyzer_template_path: Optional[str] = None,
    ) -> requests.Response:
        """
        Create an analyzer with the given ID and template.
        
        Args:
            analyzer_id: Unique identifier for the analyzer
            analyzer_template: Dict containing analyzer configuration
            analyzer_template_path: Path to JSON file with analyzer config
            
        Returns:
            Response object from the API
        """
        # Load template from file if path provided
        if analyzer_template_path and Path(analyzer_template_path).exists():
            with open(analyzer_template_path, "r") as f:
                analyzer_template = json.load(f)
        
        if not analyzer_template:
            raise ValueError("Analyzer template must be provided.")
        
        headers = {"Content-Type": "application/json"}
        headers.update(self._get_headers())
        
        response = requests.put(
            url=self._get_analyzer_url(analyzer_id),
            headers=headers,
            json=analyzer_template,
        )
        
        if not response.ok:
            logger.error(f"Analyzer creation failed: {response.status_code} - {response.text}")
        
        response.raise_for_status()
        logger.info(f"Analyzer {analyzer_id} create request accepted.")
        return response
    
    def delete_analyzer(self, analyzer_id: str) -> requests.Response:
        """Delete an analyzer."""
        response = requests.delete(
            url=self._get_analyzer_url(analyzer_id),
            headers=self._get_headers(),
        )
        response.raise_for_status()
        logger.info(f"Analyzer {analyzer_id} deleted.")
        return response
    
    def begin_analyze(
        self,
        analyzer_id: str,
        file_content: bytes,
        content_type: str = "application/pdf",
    ) -> requests.Response:
        """
        Begin analysis of a document using binary content.
        
        Uses the :analyzeBinary endpoint with raw bytes (GA API 2025-11-01).
        
        Args:
            analyzer_id: ID of the analyzer to use
            file_content: Raw bytes of the file to analyze
            content_type: MIME type of the file (used for logging only)
            
        Returns:
            Response object (use poll_result to get final result)
        """
        # CRITICAL: Use :analyzeBinary endpoint with application/octet-stream
        # NOT :analyze with JSON body - that's for URL-based analysis only
        headers = {"Content-Type": "application/octet-stream"}
        headers.update(self._get_headers())
        
        url = self._get_analyze_binary_url(analyzer_id)
        logger.info(f"Sending analyze request to {url}")
        logger.info(f"Original content-type: {content_type}, Content size: {len(file_content)} bytes")
        
        response = requests.post(
            url=url,
            headers=headers,
            data=file_content,  # Send raw bytes, NOT JSON
        )
        
        if not response.ok:
            logger.error(f"Analyze request failed: {response.status_code} - {response.text}")
        
        response.raise_for_status()
        logger.info(f"Analysis started with analyzer {analyzer_id}")
        return response
    
    def begin_analyze_from_url(
        self,
        analyzer_id: str,
        file_url: str,
    ) -> requests.Response:
        """
        Begin analysis of a document from URL.
        
        Uses the :analyze endpoint with JSON body (GA API 2025-11-01).
        
        Args:
            analyzer_id: ID of the analyzer to use
            file_url: URL of the file to analyze (must be accessible)
            
        Returns:
            Response object (use poll_result to get final result)
        """
        headers = {"Content-Type": "application/json"}
        headers.update(self._get_headers())
        
        # CRITICAL: URL must be wrapped in inputs array per GA API spec
        body = {"inputs": [{"url": file_url}]}
        
        response = requests.post(
            url=self._get_analyze_url(analyzer_id),
            headers=headers,
            json=body,
        )
        response.raise_for_status()
        logger.info(f"Analysis started from URL with analyzer {analyzer_id}")
        return response
    
    def poll_result(
        self,
        response: requests.Response,
        timeout_seconds: int = 300,
        polling_interval_seconds: int = 2,
    ) -> Dict[str, Any]:
        """
        Poll for the result of an async operation.
        
        Args:
            response: Response from begin_analyze
            timeout_seconds: Maximum time to wait
            polling_interval_seconds: Time between polls
            
        Returns:
            Final result dict with 'result' containing analysis output
        """
        operation_location = response.headers.get("operation-location", "")
        if not operation_location:
            raise ValueError("Operation location not found in response headers.")
        
        headers = {"Content-Type": "application/json"}
        headers.update(self._get_headers())
        
        start_time = time.time()
        
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout_seconds:
                raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds.")
            
            poll_response = requests.get(operation_location, headers=self._get_headers())
            poll_response.raise_for_status()
            
            result = poll_response.json()
            status = result.get("status", "").lower()
            
            if status == "succeeded":
                logger.info(f"Analysis completed in {elapsed_time:.1f} seconds.")
                return result
            elif status == "failed":
                error_msg = result.get("error", {}).get("message", "Unknown error")
                logger.error(f"Analysis failed: {error_msg}")
                raise RuntimeError(f"Analysis failed: {error_msg}")
            else:
                logger.debug(f"Analysis in progress... ({elapsed_time:.1f}s)")
            
            time.sleep(polling_interval_seconds)
    
    def analyze_document(
        self,
        analyzer_id: str,
        file_content: bytes,
        content_type: str = "application/pdf",
        timeout_seconds: int = 300,
    ) -> Dict[str, Any]:
        """
        Convenience method: analyze a document and wait for result.
        
        Args:
            analyzer_id: ID of the analyzer to use
            file_content: Raw bytes of the file
            content_type: MIME type
            timeout_seconds: Maximum wait time
            
        Returns:
            Analysis result dict
        """
        response = self.begin_analyze(analyzer_id, file_content, content_type)
        return self.poll_result(response, timeout_seconds)
